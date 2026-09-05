"""Recurring billing: immutable prices, provider-authoritative invoices, durable recovery."""
import hashlib
import hmac
import re
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from urllib.parse import urlparse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.organizations.models import Organization
from .models import Plan, Subscription, BillingTransaction, RecurringAgreement, RecurringCharge
from .payments import gateway, account_scope, payment_available, PaymentUnavailable, ADDON_PRICE
from .services import SubscriptionEntitlementService, CurrencyService

TERMINAL = ("cancelled", "completed", "expired", "failed")
PROVIDER_STATES = ("created", "authenticated", "active", "pending", "halted", "paused", "cancelled", "completed", "expired")


def identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r"_[A-Za-z0-9]+", value):
        raise ValidationError("Invalid payment reference.")
    return value


def timestamp(value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValidationError("The provider has not confirmed the billing period yet.")
    try:
        return datetime.fromtimestamp(value, tz=dt_timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ValidationError("Invalid billing period.") from None


def agreements(org):
    return RecurringAgreement.objects.filter(organization=org, account_scope=account_scope())


def checkout_data(agreement):
    return {"id": str(agreement.pk), "subscription_id": agreement.provider_id,
        "key": settings.RAZORPAY_KEY_ID, "amount": int(agreement.amount * 100),
        "currency": agreement.currency, "product": agreement.product,
        "description": f"{agreement.plan.name if agreement.product == 'plan' else 'DM Automation'} — monthly subscription",
        "total_count": agreement.total_count, "auto_renews": True,
        "test_mode": settings.RAZORPAY_KEY_ID.startswith("rzp_test_")}


def create_recurring(org, *, product="plan", plan_code="", country="IN"):
    if not payment_available():
        raise PaymentUnavailable()
    if not 1 <= settings.RAZORPAY_SUBSCRIPTION_CYCLES <= 1200:
        raise PaymentUnavailable("The billing cycle configuration is invalid.")
    SubscriptionEntitlementService.seed_default_plans()
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=org.pk)
        sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
        pending = agreements(org).filter(product=product).exclude(status__in=TERMINAL).first()
        if pending:
            if pending.status == "created" and pending.provider_id and (
                product == "dm_automation" or (pending.plan.code == plan_code and pending.country == country)
            ):
                return checkout_data(pending)
            raise ValidationError("A subscription for this product already exists. Check its payment status or cancel it before starting another.")
        if product == "dm_automation":
            if not sub.is_valid or sub.plan.code != "starter" or sub.cancel_at_period_end:
                raise ValidationError("An active Starter plan that is not scheduled to end is required for DM Automation.")
            plan, amount, country, currency = sub.plan, ADDON_PRICE, "IN", "INR"
            start_at = sub.automation_addon_end
        else:
            plan = Plan.objects.filter(code=plan_code, is_active=True).exclude(code="free").first()
            if not plan:
                raise ValidationError("Choose an available paid plan.")
            country, currency = CurrencyService.resolve_billing_country_and_currency(country, org)
            amount = CurrencyService.get_plan_price(plan, currency)
            # Existing paid access is honoured: the first full charge starts at its expiry.
            start_at = sub.current_period_end if sub.plan.code != "free" and sub.is_valid else None
        if amount <= 0:
            raise ValidationError("The selected paid product must have a positive price.")
        intent = RecurringAgreement.objects.create(organization=org, product=product, plan=plan,
            amount=amount, country=country, currency=currency, account_scope=account_scope(),
            total_count=settings.RAZORPAY_SUBSCRIPTION_CYCLES)
    try:
        remote_plan = gateway("POST", "plans", {"period": "monthly", "interval": 1,
            "item": {"name": f"Nextora {plan.name if product == 'plan' else 'DM Automation'}",
                "amount": int(amount * 100), "currency": currency},
            "notes": {"billing_agreement_id": str(intent.pk)}})
        if (not isinstance(remote_plan, dict) or remote_plan.get("item", {}).get("amount") != int(amount * 100)
                or remote_plan.get("item", {}).get("currency") != currency):
            raise PaymentUnavailable("Razorpay returned an unexpected plan. Contact support before retrying.")
        intent.provider_plan_id = identifier(remote_plan.get("id"), "plan")
        intent.save(update_fields=["provider_plan_id", "updated_at"])
        payload = {"plan_id": intent.provider_plan_id, "total_count": intent.total_count,
            "quantity": 1, "customer_notify": True,
            "expire_by": int((timezone.now() + timezone.timedelta(days=1)).timestamp()),
            "notes": {"billing_agreement_id": str(intent.pk), "organization_id": str(org.pk)}}
        if start_at and start_at > timezone.now() + timezone.timedelta(minutes=5):
            payload["start_at"] = int(start_at.timestamp())
        remote = gateway("POST", "subscriptions", payload)
        attach_provider(intent, remote)
    except Exception as exc:
        # An uncertain POST is never repeated: a recovery scan matches the immutable intent note.
        RecurringAgreement.objects.filter(pk=intent.pk).update(
            status="failed" if getattr(exc, "definitive", False) else "creating",
            last_error="Checkout creation could not be confirmed. Use Check payment status.")
        raise
    intent.refresh_from_db()
    return checkout_data(intent)


def validate_remote(agreement, remote):
    if (not isinstance(remote, dict) or remote.get("id") != agreement.provider_id
            or remote.get("plan_id") != agreement.provider_plan_id or remote.get("quantity") != 1
            or remote.get("status") not in PROVIDER_STATES):
        raise ValidationError("Subscription verification returned an unexpected result.")


def attach_provider(agreement, remote):
    if not isinstance(remote, dict):
        raise PaymentUnavailable("Razorpay returned an invalid subscription.")
    agreement.provider_id = identifier(remote.get("id"), "sub")
    validate_remote(agreement, remote)
    with transaction.atomic():
        current = RecurringAgreement.objects.select_for_update().get(pk=agreement.pk)
        if current.provider_id and current.provider_id != agreement.provider_id:
            raise ValidationError("Multiple provider subscriptions require manual review.")
        current.provider_id = agreement.provider_id
        current.status = remote["status"]
        url = remote.get("short_url", "") or ""
        current.short_url = url if urlparse(url).scheme == "https" and urlparse(url).hostname in ("rzp.io", "rzp.me", "razorpay.com") else ""
        current.last_error = ""
        current.save()


def recover_creation(agreement):
    if agreement.provider_id:
        return
    # Do not race a request still creating its remote subscription.
    if agreement.created_at > timezone.now() - timezone.timedelta(minutes=1):
        raise PaymentUnavailable("Checkout is still being confirmed. Check again in a minute.")
    found = []
    for skip in range(0, 2000, 100):
        batch = gateway("GET", f"subscriptions?count=100&skip={skip}")
        items = batch.get("items") if isinstance(batch, dict) else None
        if not isinstance(items, list):
            raise PaymentUnavailable("Razorpay subscription recovery is temporarily unavailable.")
        found.extend(item for item in items if isinstance(item.get("notes"), dict)
            and item["notes"].get("billing_agreement_id") == str(agreement.pk))
        if len(items) < 100:
            break
    if len(found) == 1:
        attach_provider(agreement, found[0])
        agreement.refresh_from_db()
    else:
        raise PaymentUnavailable("An earlier checkout needs administrator reconciliation before another mandate can be created.")


def apply_invoice(agreement, invoice, payment):
    """All arguments originate from authenticated provider GETs, never browser amounts."""
    amount = int(agreement.amount * 100)
    invoice_id = identifier(invoice.get("id"), "inv")
    payment_id = identifier(payment.get("id"), "pay")
    if (invoice.get("subscription_id") != agreement.provider_id or invoice.get("payment_id") != payment_id
        or invoice.get("order_id") != payment.get("order_id") or payment.get("invoice_id") != invoice_id
        or invoice.get("status") != "paid" or invoice.get("amount") != amount
        or invoice.get("amount_paid") != amount or invoice.get("currency") != agreement.currency
        or payment.get("amount") != amount or payment.get("currency") != agreement.currency
        or payment.get("status") not in ("captured", "refunded")):
        raise ValidationError("Paid invoice does not match the authorized subscription, amount and currency.")
    start, end = timestamp(invoice.get("billing_start")), timestamp(invoice.get("billing_end"))
    if end <= start:
        raise ValidationError("Invalid paid billing period.")
    refunded = payment.get("amount_refunded") or 0
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=agreement.organization_id)
        charge = RecurringCharge.objects.select_related("transaction").filter(invoice_id=invoice_id).first()
        new_charge = charge is None
        if charge:
            if charge.agreement_id != agreement.pk or charge.payment_id != payment_id:
                raise ValidationError("This invoice is already assigned to another subscription.")
            tx = charge.transaction
        else:
            if RecurringCharge.objects.filter(payment_id=payment_id).exists():
                raise ValidationError("This payment is already assigned to another invoice.")
            sub = Subscription.objects.get(organization_id=agreement.organization_id)
            tx = BillingTransaction.objects.create(organization_id=agreement.organization_id, subscription=sub,
                provider="razorpay", provider_payment_id=payment_id, provider_order_id=invoice["order_id"],
                amount=agreement.amount, currency=agreement.currency, status="success",
                paid_at=timestamp(invoice.get("paid_at") or payment.get("created_at")),
                payment_metadata={"product": agreement.product, "plan_code": agreement.plan.code,
                    "agreement_id": str(agreement.pk), "invoice_id": invoice_id, "recurring": True,
                    "billing_start": invoice["billing_start"], "billing_end": invoice["billing_end"], "entitlement_applied": False})
            charge = RecurringCharge.objects.create(agreement=agreement, invoice_id=invoice_id,
                payment_id=payment_id, transaction=tx, period_start=start, period_end=end)
        # Refresh refund status without replaying the entitlement grant.
        tx.payment_metadata["refunded_amount"] = refunded
        tx.status = "refunded" if refunded >= amount else "partially_refunded" if refunded else "success"
        tx.save(update_fields=["status", "payment_metadata", "updated_at"])
        sub = Subscription.objects.select_related("plan").get(organization_id=agreement.organization_id)
        current_end = sub.automation_addon_end if agreement.product == "dm_automation" else sub.current_period_end
        current_start = sub.automation_addon_start if agreement.product == "dm_automation" else sub.current_period_start
        paid_current = current_end == end and current_start == start
        # Older invoices never move paid access backwards or reset monthly quotas.
        unapplied = not tx.payment_metadata.get("entitlement_applied", not new_charge)
        grant = unapplied and (not current_end or end > current_end)
        if unapplied and agreement.product == "plan" and sub.plan.code == "free":
            grant = True
        grant = grant and start <= timezone.now() < end
        if refunded >= amount:
            if paid_current:
                if agreement.product == "plan": sub.status = "expired"
                else: sub.automation_addon_end = min(end, timezone.now())
        elif grant:
            if agreement.product == "dm_automation":
                sub.automation_addon_start, sub.automation_addon_end = start, end
                sub.automation_billing_account = agreement.account_scope
            else:
                sub.plan = agreement.plan
                sub.current_period_start, sub.current_period_end = start, end
                sub.status, sub.charged_amount = "active", agreement.amount
                sub.billing_country, sub.billing_currency = agreement.country, agreement.currency
                sub.provider_subscription_id = agreement.provider_id
                sub.billing_account = agreement.account_scope
                sub.cancel_at_period_end = agreement.cancel_at_period_end
        sub.save()
        if grant or refunded >= amount:
            tx.payment_metadata["entitlement_applied"] = True
            tx.save(update_fields=["payment_metadata", "updated_at"])
    return charge


def reconcile_agreement(agreement_id):
    agreement = RecurringAgreement.objects.select_related("plan").get(pk=agreement_id, account_scope=account_scope())
    recover_creation(agreement)
    # Serialise provider snapshots too: concurrent syncs must not apply stale statuses last.
    with transaction.atomic():
        Organization.objects.select_for_update().get(pk=agreement.organization_id)
        agreement = RecurringAgreement.objects.select_for_update().select_related("plan").get(pk=agreement_id)
        remote = gateway("GET", f"subscriptions/{agreement.provider_id}")
        validate_remote(agreement, remote)
        # The mandate price is immutable, even if an administrator later changes the catalogue.
        plan = gateway("GET", f"plans/{agreement.provider_plan_id}")
        if (plan.get("item", {}).get("amount") != int(agreement.amount * 100)
            or plan.get("item", {}).get("currency") != agreement.currency
            or plan.get("period") != "monthly" or plan.get("interval") != 1):
            raise ValidationError("The provider plan differs from the authorized billing terms.")
        for skip in range(0, 2000, 100):
            batch = gateway("GET", f"invoices?subscription_id={agreement.provider_id}&count=100&skip={skip}")
            items = batch.get("items") if isinstance(batch, dict) else None
            if not isinstance(items, list):
                raise PaymentUnavailable("Invoice verification is temporarily unavailable.")
            for invoice in sorted(items, key=lambda item: item.get("billing_end") or 0):
                if invoice.get("status") != "paid": continue
                if (invoice.get("billing_end") and remote.get("current_start")
                    and invoice["billing_end"] < remote["current_start"]
                    and RecurringCharge.objects.filter(invoice_id=invoice.get("id")).exists()):
                    continue
                payment_id = identifier(invoice.get("payment_id"), "pay")
                payment = gateway("GET", f"payments/{payment_id}")
                apply_invoice(agreement, invoice, payment)
            if len(items) < 100: break
        agreement.status = remote["status"]
        if remote.get("cancel_at_cycle_end") is True or remote.get("cancel_at_cycle_end") == 1:
            agreement.cancel_at_period_end = True
        agreement.paid_count = remote.get("paid_count", 0)
        agreement.current_start = timestamp(remote["current_start"]) if remote.get("current_start") else None
        agreement.current_end = timestamp(remote["current_end"]) if remote.get("current_end") else None
        agreement.last_synced_at, agreement.last_error = timezone.now(), ""
        agreement.save()
        sub = Subscription.objects.get(organization_id=agreement.organization_id)
        if agreement.product == "plan" and sub.provider_subscription_id == agreement.provider_id:
            sub.cancel_at_period_end = agreement.cancel_at_period_end
            # Failure/cancellation stops future access, but never erases an already paid period.
            if remote["status"] in ("pending", "halted", "paused") and not sub.is_valid:
                sub.status = "past_due"
            if remote["status"] in TERMINAL:
                sub.cancel_at_period_end = True
                if not sub.is_valid: sub.status = "cancelled" if remote["status"] == "cancelled" else "expired"
            sub.save()
    # Dashboard-side mandate cancellation must also stop the dependent add-on.
    if (agreement.product == "plan" and sub.provider_subscription_id == agreement.provider_id
        and (agreement.status in TERMINAL or agreement.status == "halted" or agreement.cancel_at_period_end)):
        cancel_recurring(agreement.organization, "dm_automation")
    if agreement.product == "dm_automation" and (not sub.is_valid or sub.plan.code != "starter" or sub.cancel_at_period_end):
        cancel_recurring(agreement.organization, "dm_automation")
    return agreement


def verify_recurring(org, subscription_id, payment_id, signature):
    identifier(subscription_id, "sub")
    identifier(payment_id, "pay")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise ValidationError("Invalid payment signature.")
    agreement = agreements(org).filter(provider_id=subscription_id).first()
    if not agreement: raise ValidationError("This subscription does not belong to the workspace.")
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{payment_id}|{agreement.provider_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature): raise ValidationError("Invalid payment signature.")
    # Authentication alone (including a refundable mandate token payment) never grants a paid plan.
    return reconcile_agreement(agreement.pk)


def cancel_recurring(org, product="plan"):
    products = ["dm_automation", "plan"] if product == "plan" else ["dm_automation"]
    for item in products:
        for agreement in agreements(org).filter(product=item).exclude(status__in=TERMINAL):
            recover_creation(agreement)
            with transaction.atomic():
                Organization.objects.select_for_update().get(pk=org.pk)
                agreement = RecurringAgreement.objects.select_for_update().get(pk=agreement.pk)
                if agreement.cancel_at_period_end: continue
                remote = gateway("GET", f"subscriptions/{agreement.provider_id}")
                validate_remote(agreement, remote)
                if remote["status"] not in TERMINAL:
                    at_end = remote["status"] == "active" and (remote.get("remaining_count") or 0) > 1
                    remote = gateway("POST", f"subscriptions/{agreement.provider_id}/cancel", {"cancel_at_cycle_end": at_end})
                    validate_remote(agreement, remote)
                agreement.status = remote["status"]
                agreement.cancel_at_period_end = True
                agreement.save()
    if product == "plan":
        Subscription.objects.filter(organization=org).update(cancel_at_period_end=True)
    return {"message": "Automatic renewal stopped. Access remains available until the end of the paid period."}
