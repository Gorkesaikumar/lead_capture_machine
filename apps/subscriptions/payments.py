"""Razorpay checkout: server-priced orders, verified capture, idempotent grants.

Monthly access is renewed by checkout; this is not an automatic debit mandate.
"""
import hashlib
import hmac
import re
from decimal import Decimal
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError
from apps.organizations.models import Organization
from .models import Plan, Subscription, BillingTransaction

ADDON_PRICE = Decimal("399.00")


class PaymentUnavailable(APIException):
    status_code = 503
    default_code = "payment_unavailable"
    default_detail = "Payments are not configured. Contact the workspace administrator."


def payment_available():
    return bool(getattr(settings, "RAZORPAY_KEY_ID", "") and getattr(settings, "RAZORPAY_KEY_SECRET", ""))


def account_scope():
    return hashlib.sha256(settings.RAZORPAY_KEY_ID.encode()).hexdigest()


def gateway(method, path, payload=None):
    if not payment_available():
        raise PaymentUnavailable()
    try:
        response = requests.request(method, f"https://api.razorpay.com/v1/{path}",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET), json=payload, timeout=15)
        if not response.ok:
            error = PaymentUnavailable("Razorpay could not complete this request. Check payment status before trying again.")
            error.definitive = 400 <= response.status_code < 500 and response.status_code not in (408, 409, 429)
            raise error
        return response.json()
    except (requests.RequestException, ValueError):
        raise PaymentUnavailable("The payment provider could not be reached. Check payment status before retrying.") from None


def create_order(org, *, product="plan", plan_code="", country="IN"):
    from .services import SubscriptionEntitlementService, CurrencyService
    if product not in ("plan", "dm_automation"):
        raise ValidationError("Unknown billing product.")
    if not payment_available():
        raise PaymentUnavailable()
    from .recurring import agreements, TERMINAL
    if agreements(org).filter(product=product).exclude(status__in=TERMINAL).exists():
        raise ValidationError("This product already has automatic billing. Manage the existing subscription.")
    SubscriptionEntitlementService.seed_default_plans()
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=org.pk)
        sub = Subscription.objects.select_related("plan").filter(organization=org).first()
        if not sub:
            sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
        if product == "dm_automation":
            if not sub or not sub.is_valid or sub.plan.code != Plan.Code.STARTER:
                raise ValidationError("The ₹399 DM Automation add-on requires an active Starter plan. Creator and Enterprise include automation.")
            if sub.automation_addon_end and sub.automation_addon_end > timezone.now():
                raise ValidationError("The automation add-on is already paid through its expiry date.")
            amount, currency, country = ADDON_PRICE, "INR", "IN"
            plan_code = "starter"
        else:
            plan = Plan.objects.filter(code=plan_code, is_active=True).first()
            if not plan or plan.code == Plan.Code.FREE:
                raise ValidationError("Select a paid plan. To end a paid plan, use Cancel subscription.")
            if sub and sub.plan_id == plan.pk and sub.is_valid:
                raise ValidationError("This plan is already active. Renew after the paid period ends.")
            country, currency = CurrencyService.resolve_billing_country_and_currency(country, org)
            amount = CurrencyService.get_plan_price(plan, currency)
        # Reuse the same unpaid order on double-clicks and page reloads.
        pending = BillingTransaction.objects.filter(organization=org, status="pending", provider="razorpay",
            payment_metadata__product=product, payment_metadata__plan_code=plan_code,
            amount=amount, currency=currency).first()
        if pending:
            if not pending.provider_order_id:
                raise PaymentUnavailable("A previous checkout is unconfirmed. Contact support before starting another payment.")
            tx = pending
        else:
            tx = BillingTransaction.objects.create(organization=org, subscription=sub, provider="razorpay",
                amount=amount, currency=currency, payment_metadata={"product": product, "plan_code": plan_code,
                "country": country, "price_verified": True})
            # Persist the intent before contacting the provider; an uncertain POST is not auto-retried.
    if not tx.provider_order_id:
        result = gateway("POST", "orders", {"amount": int(tx.amount*100), "currency": tx.currency, "receipt": tx.pk.hex})
        if not isinstance(result, dict) or not re.fullmatch(r"order_[A-Za-z0-9]+", str(result.get("id", ""))) or result.get("amount") != int(tx.amount*100) or result.get("currency") != tx.currency:
            raise PaymentUnavailable("The provider returned an invalid payment order. Access has not been activated.")
        tx.provider_order_id = result["id"]
        tx.save(update_fields=["provider_order_id", "updated_at"])
    return {"order_id": tx.provider_order_id, "key": settings.RAZORPAY_KEY_ID,
        "amount": int(tx.amount*100), "currency": tx.currency, "product": product,
        "description": "DM Automation: one month" if product == "dm_automation" else f"{plan_code.title()} plan: one month"}


def apply_capture(tx_id, payment):
    from apps.automations.usage import next_month
    initial = BillingTransaction.objects.get(pk=tx_id)
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=initial.organization_id)
        tx = BillingTransaction.objects.select_for_update().get(pk=tx_id)
        if (payment.get("order_id") != tx.provider_order_id or payment.get("amount") != int(tx.amount*100)
                or payment.get("currency") != tx.currency or payment.get("status") != "captured"
                or not re.fullmatch(r"pay_[A-Za-z0-9]+", str(payment.get("id", "")))):
            raise ValidationError("Payment is not captured for this exact order, amount and currency. Access has not been activated.")
        if not tx.payment_metadata.get("price_verified"):
            raise ValidationError("Legacy unverified orders cannot activate paid access.")
        if tx.status == "success":
            if tx.provider_payment_id != payment["id"]:
                raise ValidationError("This order was already fulfilled by another payment.")
            return Subscription.objects.select_related("plan").get(organization_id=tx.organization_id)
        now = timezone.now()
        sub = Subscription.objects.select_related("plan").get(organization_id=tx.organization_id)
        if tx.payment_metadata["product"] == "dm_automation":
            # Grant the paid month even if a base plan expired during checkout; entitlement
            # still requires Starter. Keep the ledger for reconciliation/refunds.
            start = max(now, sub.automation_addon_end) if sub.automation_addon_end else now
            sub.automation_addon_start, sub.automation_addon_end = start, next_month(start)
        else:
            sub.plan = Plan.objects.get(code=tx.payment_metadata["plan_code"])
            sub.status, sub.charged_amount = "active", tx.amount
            sub.billing_country, sub.billing_currency = tx.payment_metadata["country"], tx.currency
            sub.current_period_start, sub.current_period_end = now, next_month(now)
            sub.cancel_at_period_end = False
        sub.save()
        tx.subscription, tx.status, tx.provider_payment_id, tx.paid_at = sub, "success", payment["id"], now
        tx.save()
        return sub


def verify_checkout(org, order_id, payment_id, signature):
    if (not all(isinstance(v, str) for v in (order_id, payment_id, signature))
            or not re.fullmatch(r"pay_[A-Za-z0-9]+", payment_id) or not re.fullmatch(r"[0-9a-f]{64}", signature)):
        raise ValidationError("A real provider payment ID and signature are required.")
    tx = BillingTransaction.objects.filter(organization=org, provider="razorpay", provider_order_id=order_id).first()
    if not tx:
        raise ValidationError("Payment order not found in this workspace.")
    if not payment_available():
        raise PaymentUnavailable()
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{tx.provider_order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValidationError("Payment signature is invalid. Access has not been activated.")
    payment = gateway("GET", f"payments/{payment_id}")
    if not isinstance(payment, dict) or payment.get("id") != payment_id:
        raise ValidationError("Payment verification returned an unexpected result.")
    return apply_capture(tx.pk, payment)
