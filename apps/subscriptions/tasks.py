import logging
import re
from celery import shared_task
from django.db.models import F, Q
from django.utils import timezone
from .models import RecurringAgreement, RecurringCharge, PaymentWebhookEvent, BillingTransaction
from .payments import account_scope, payment_available, gateway, PaymentUnavailable
from .recurring import reconcile_agreement, apply_invoice, identifier, attach_provider, TERMINAL

logger = logging.getLogger(__name__)


def enqueue_webhook(event_id):
    try:
        process_payment_webhook.delay(event_id)
    except Exception:
        # The inbox row is already durable; beat will retry even if the broker is down.
        logger.warning("Payment webhook queued for recovery: %s", event_id)


@shared_task(soft_time_limit=240, time_limit=270)
def process_payment_webhook(event_id):
    event = PaymentWebhookEvent.objects.get(pk=event_id)
    if event.is_processed: return
    PaymentWebhookEvent.objects.filter(pk=event_id).update(attempts=F("attempts") + 1)
    try:
        data = event.payload
        if data.get("account_scope") != account_scope():
            raise PaymentUnavailable("Webhook belongs to a different payment account.")
        sub_id, invoice_id, payment_id = data.get("subscription_id"), data.get("invoice_id"), data.get("payment_id")
        payment = None
        if payment_id and not invoice_id:
            payment = gateway("GET", f"payments/{identifier(payment_id, 'pay')}")
            invoice_id = payment.get("invoice_id")
        invoice = gateway("GET", f"invoices/{identifier(invoice_id, 'inv')}") if invoice_id else None
        if invoice:
            sub_id = invoice.get("subscription_id")
        agreement = RecurringAgreement.objects.filter(provider_id=sub_id, account_scope=account_scope()).first() if sub_id else None
        if not agreement and sub_id:
            remote = gateway("GET", f"subscriptions/{identifier(sub_id, 'sub')}")
            notes = remote.get("notes") or {}
            local_id = notes.get("billing_agreement_id") if isinstance(notes, dict) else None
            if isinstance(local_id, str) and re.fullmatch(r"[0-9a-f-]{36}", local_id):
                agreement = RecurringAgreement.objects.filter(pk=local_id, account_scope=account_scope()).first()
                if agreement: attach_provider(agreement, remote)
        if agreement:
            reconcile_agreement(agreement.pk)
            if invoice and invoice.get("status") == "paid":
                payment = gateway("GET", f"payments/{identifier(invoice.get('payment_id'), 'pay')}")
                apply_invoice(agreement, invoice, payment)
        elif data.get("order_id"):
            # Honour pre-existing one-off orders during migration to recurring billing.
            from .payments import apply_capture
            tx = BillingTransaction.objects.filter(provider_order_id=data["order_id"], payment_metadata__price_verified=True).first()
            if tx and data["event_type"] in ("payment.captured", "order.paid"):
                payment = gateway("GET", f"payments/{identifier(payment_id, 'pay')}")
                apply_capture(tx.pk, payment)
        PaymentWebhookEvent.objects.filter(pk=event_id).update(is_processed=True, processed_at=timezone.now(), last_error="")
    except Exception as exc:
        PaymentWebhookEvent.objects.filter(pk=event_id).update(last_error="Provider reconciliation failed; retry pending.", updated_at=timezone.now())
        logger.warning("Payment event %s needs recovery (%s)", event_id, type(exc).__name__)
        # Periodic inbox recovery retries; never log provider payloads or payer details.


@shared_task(soft_time_limit=240, time_limit=270)
def reconcile_recurring_payments():
    if not payment_available(): return
    events = PaymentWebhookEvent.objects.filter(is_processed=False, event_id__startswith="recurring:",
        payload__account_scope=account_scope()).order_by("updated_at")[:50]
    for event in events:
        process_payment_webhook.delay(str(event.pk))
    candidates = RecurringAgreement.objects.filter(account_scope=account_scope()).filter(
        ~Q(status__in=TERMINAL) | Q(updated_at__gte=timezone.now() - timezone.timedelta(days=2))
    ).order_by(F("last_synced_at").asc(nulls_first=True), "created_at")[:50]
    for agreement in candidates:
        reconcile_one_agreement.delay(str(agreement.pk))


@shared_task(soft_time_limit=240, time_limit=270)
def reconcile_one_agreement(agreement_id):
    try:
        reconcile_agreement(agreement_id)
    except Exception as exc:
        RecurringAgreement.objects.filter(pk=agreement_id).update(last_error="Payment reconciliation pending; check again shortly.", last_synced_at=timezone.now())
        logger.warning("Subscription %s needs recovery (%s)", agreement_id, type(exc).__name__)
