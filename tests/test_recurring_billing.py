import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.subscriptions.models import Plan, Subscription, RecurringAgreement, RecurringCharge, BillingTransaction, PaymentWebhookEvent
from apps.subscriptions.services import SubscriptionEntitlementService
from apps.subscriptions.payments import account_scope, PaymentUnavailable
from apps.subscriptions.recurring import create_recurring, apply_invoice, reconcile_agreement, verify_recurring, cancel_recurring, recover_creation

pytestmark = pytest.mark.django_db


@pytest.fixture
def billing(settings):
    settings.RAZORPAY_KEY_ID = "rzp_test_recurring"
    settings.RAZORPAY_KEY_SECRET = "test-signing-key"
    settings.RAZORPAY_WEBHOOK_SECRET = "test-webhook-key"
    settings.RAZORPAY_SUBSCRIPTION_CYCLES = 120
    user = User.objects.create_user(email="billing-recurring@example.test")
    org = Organization.objects.create(name="Billing Test", slug="billing-test", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    sub = SubscriptionEntitlementService.get_or_create_active_subscription(org)
    client = APIClient()
    client.force_authenticate(user)
    return org, sub, client


def make_agreement(org, **kwargs):
    return RecurringAgreement.objects.create(organization=org, product="plan", plan=Plan.objects.get(code="starter"),
        amount=Decimal("400.00"), currency="INR", country="IN", provider_id="sub_test", provider_plan_id="plan_test",
        account_scope=account_scope(), **kwargs)


def entities(agreement, suffix="one", offset=0):
    start = int((timezone.now() - timezone.timedelta(hours=1) + timezone.timedelta(days=30 * offset)).timestamp())
    end = start + 30 * 86400
    invoice = {"id": "inv_" + suffix, "subscription_id": agreement.provider_id, "order_id": "order_" + suffix,
        "payment_id": "pay_" + suffix, "status": "paid", "amount": 40000, "amount_paid": 40000, "currency": "INR",
        "billing_start": start, "billing_end": end, "paid_at": start}
    payment = {"id": "pay_" + suffix, "invoice_id": invoice["id"], "order_id": invoice["order_id"], "amount": 40000,
        "currency": "INR", "status": "captured", "amount_refunded": 0, "created_at": start}
    remote = {"id": agreement.provider_id, "plan_id": agreement.provider_plan_id, "quantity": 1, "status": "active",
        "current_start": start, "current_end": end, "paid_count": offset + 1, "remaining_count": 119-offset}
    return invoice, payment, remote


def provider(agreement, invoice=None, payment=None, remote=None):
    def call(method, path, payload=None):
        if path == f"subscriptions/{agreement.provider_id}": return remote
        if path == f"plans/{agreement.provider_plan_id}": return {"period": "monthly", "interval": 1, "item": {"amount": 40000, "currency": "INR"}}
        if path.startswith("invoices?"): return {"items": [invoice] if invoice else []}
        if payment and path == f"payments/{payment['id']}": return payment
        raise AssertionError((method, path, payload))
    return call


def test_future_paid_invoice_waits_until_period_start(billing):
    org, sub, _ = billing
    agreement = make_agreement(org)
    invoice, payment, _ = entities(agreement, offset=1)
    apply_invoice(agreement, invoice, payment)
    sub.refresh_from_db()
    assert sub.plan.code == "free"
    assert RecurringCharge.objects.count() == 1
    with patch("apps.subscriptions.recurring.timezone.now", return_value=timezone.datetime.fromtimestamp(invoice["billing_start"] + 60, tz=timezone.get_current_timezone())):
        apply_invoice(agreement, invoice, payment)
    sub.refresh_from_db()
    assert sub.plan.code == "starter"
    assert RecurringCharge.objects.count() == 1


def test_provider_base_cancellation_stops_dependent_addon(billing):
    org, sub, _ = billing
    agreement = make_agreement(org)
    invoice, payment, remote = entities(agreement)
    apply_invoice(agreement, invoice, payment)
    remote["status"] = "cancelled"
    with patch("apps.subscriptions.recurring.gateway", side_effect=provider(agreement, invoice, payment, remote)), patch("apps.subscriptions.recurring.cancel_recurring") as stop:
        reconcile_agreement(agreement.pk)
    stop.assert_called_once_with(org, "dm_automation")


def test_creation_uses_catalogue_price_and_reuses_pending_mandate(billing):
    org, sub, client = billing
    plan = Plan.objects.get(code="starter")
    plan.price_inr = Decimal("450.00")
    plan.save()
    with patch("apps.subscriptions.recurring.gateway", side_effect=[
        {"id": "plan_new", "item": {"amount": 45000, "currency": "INR"}},
        {"id": "sub_new", "plan_id": "plan_new", "quantity": 1, "status": "created", "short_url": "https://rzp.io/test"},
    ]) as mock:
        response = client.post("/api/v1/subscriptions/recurring/checkout/", {"plan_code": "starter", "accept_recurring": True, "amount": 1}, format="json")
    assert response.status_code == 200
    assert response.data["amount"] == 45000
    assert mock.call_args_list[0].args[2]["item"]["amount"] == 45000
    assert mock.call_args_list[1].args[2]["total_count"] == 120
    with patch("apps.subscriptions.recurring.gateway") as mock:
        assert create_recurring(org, plan_code="starter")["subscription_id"] == "sub_new"
    mock.assert_not_called()
    sub.refresh_from_db()
    assert sub.plan.code == "free"
    assert "SECRET" not in json.dumps(response.data)


def test_explicit_recurring_consent_and_admin_permission_required(billing):
    org, sub, client = billing
    assert client.post("/api/v1/subscriptions/recurring/checkout/", {"plan_code": "starter"}).status_code == 400
    OrganizationMembership.objects.filter(organization=org).update(role="MEMBER")
    assert client.post("/api/v1/subscriptions/recurring/checkout/", {"plan_code": "starter", "accept_recurring": True}).status_code == 403
    assert not RecurringAgreement.objects.exists()


def test_uncertain_create_is_not_automatically_retried(billing):
    org, _, _ = billing
    with patch("apps.subscriptions.recurring.gateway", side_effect=PaymentUnavailable("Timeout")):
        with pytest.raises(PaymentUnavailable): create_recurring(org, plan_code="starter")
    assert RecurringAgreement.objects.get().status == "creating"
    with patch("apps.subscriptions.recurring.gateway") as mock:
        with pytest.raises(ValidationError): create_recurring(org, plan_code="starter")
    mock.assert_not_called()


def test_creation_recovers_by_immutable_note(billing):
    org, _, _ = billing
    a = make_agreement(org)
    a.provider_id = None
    a.created_at = timezone.now() - timezone.timedelta(minutes=5)
    a.save()
    remote = {"id": "sub_recovered", "plan_id": "plan_test", "quantity": 1, "status": "created", "notes": {"billing_agreement_id": str(a.pk)}}
    with patch("apps.subscriptions.recurring.gateway", return_value={"items": [remote]}): recover_creation(a)
    a.refresh_from_db()
    assert a.provider_id == "sub_recovered"


def test_authorization_alone_does_not_grant_paid_access(billing):
    org, sub, _ = billing
    a = make_agreement(org)
    _, _, remote = entities(a)
    remote.update(status="authenticated", current_start=None, current_end=None, paid_count=0)
    signature = hmac.new(b"test-signing-key", b"pay_token|sub_test", hashlib.sha256).hexdigest()
    with patch("apps.subscriptions.recurring.gateway", side_effect=provider(a, remote=remote)):
        verify_recurring(org, a.provider_id, "pay_token", signature)
    sub.refresh_from_db()
    assert sub.plan.code == "free" and not RecurringCharge.objects.exists()


@pytest.mark.parametrize("change", [{"amount": 1}, {"currency": "USD"}, {"status": "authorized"}, {"invoice_id": "inv_wrong"}, {"order_id": "order_wrong"}])
def test_unmatched_payment_never_grants_access(billing, change):
    org, sub, _ = billing
    a = make_agreement(org)
    invoice, payment, _ = entities(a)
    payment.update(change)
    with pytest.raises(ValidationError): apply_invoice(a, invoice, payment)
    assert not BillingTransaction.objects.exists()


def test_verified_capture_and_duplicates_use_exact_provider_period(billing):
    org, sub, _ = billing
    a = make_agreement(org)
    invoice, payment, remote = entities(a)
    with patch("apps.subscriptions.recurring.gateway", side_effect=provider(a, invoice, payment, remote)):
        reconcile_agreement(a.pk)
        reconcile_agreement(a.pk)
    sub.refresh_from_db()
    assert sub.is_valid and sub.plan.code == "starter"
    assert int(sub.current_period_end.timestamp()) == invoice["billing_end"]
    assert RecurringCharge.objects.count() == BillingTransaction.objects.count() == 1


def test_late_invoice_does_not_regress_renewed_period(billing):
    org, sub, _ = billing
    a = make_agreement(org)
    old_invoice, old_payment, _ = entities(a, offset=-1)
    invoice, payment, _ = entities(a, "renewal")
    apply_invoice(a, invoice, payment)
    apply_invoice(a, old_invoice, old_payment)
    sub.refresh_from_db()
    assert int(sub.current_period_end.timestamp()) == invoice["billing_end"]
    assert RecurringCharge.objects.count() == 2


def test_forged_or_foreign_subscription_is_rejected_before_api_calls(billing):
    org, _, _ = billing
    a = make_agreement(org)
    with patch("apps.subscriptions.recurring.gateway") as mock:
        with pytest.raises(ValidationError): verify_recurring(org, a.provider_id, "pay_one", "0"*64)
        with pytest.raises(ValidationError): verify_recurring(org, "sub_another", "pay_one", "0"*64)
    mock.assert_not_called()


def test_refund_revokes_only_refunded_period_and_is_idempotent(billing):
    org, sub, _ = billing
    a = make_agreement(org)
    invoice, payment, _ = entities(a)
    apply_invoice(a, invoice, payment)
    payment.update(amount_refunded=40000, status="refunded")
    apply_invoice(a, invoice, payment)
    apply_invoice(a, invoice, payment)
    sub.refresh_from_db()
    assert not sub.is_valid
    assert BillingTransaction.objects.get().status == "refunded"
    assert RecurringCharge.objects.count() == 1


def test_cancel_calls_provider_and_preserves_paid_period(billing):
    org, sub, _ = billing
    a = make_agreement(org, status="active")
    invoice, payment, remote = entities(a)
    apply_invoice(a, invoice, payment)
    with patch("apps.subscriptions.recurring.gateway", return_value=remote) as mock:
        cancel_recurring(org)
    assert mock.call_args.args == ("POST", "subscriptions/sub_test/cancel", {"cancel_at_cycle_end": True})
    sub.refresh_from_db()
    assert sub.is_valid and sub.cancel_at_period_end
    a.refresh_from_db()
    assert a.cancel_at_period_end


def test_failed_cancellation_is_not_reported_as_cancelled(billing):
    org, sub, _ = billing
    a = make_agreement(org, status="active")
    _, _, remote = entities(a)
    with patch("apps.subscriptions.recurring.gateway", side_effect=[remote, PaymentUnavailable("Timeout")]):
        with pytest.raises(PaymentUnavailable): cancel_recurring(org)
    a.refresh_from_db()
    assert not a.cancel_at_period_end


def test_test_mode_entitlement_cannot_carry_over_to_live_keys(billing, settings):
    org, sub, _ = billing
    a = make_agreement(org)
    invoice, payment, _ = entities(a)
    apply_invoice(a, invoice, payment)
    sub.refresh_from_db()
    assert sub.is_valid
    settings.RAZORPAY_KEY_ID = "rzp_live_other"
    assert not sub.is_valid


def test_webhook_signature_and_duplicate_event_header(billing):
    _, _, _ = billing
    client = APIClient()
    payload = {"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_test"}}}}
    body = json.dumps(payload).encode()
    url = "/api/v1/subscriptions/webhooks/razorpay/"
    assert client.post(url, body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="0"*64).status_code == 403
    assert not PaymentWebhookEvent.objects.exists()
    signature = hmac.new(b"test-webhook-key", body, hashlib.sha256).hexdigest()
    for _ in range(2):
        response = client.post(url, body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature, HTTP_X_RAZORPAY_EVENT_ID="evt_duplicate")
        assert response.status_code == 200
    assert PaymentWebhookEvent.objects.count() == 1
    event = PaymentWebhookEvent.objects.get()
    assert not event.is_processed
    assert "entity" not in event.payload


def test_payment_pending_preserves_previously_paid_access(billing):
    org, sub, _ = billing
    a = make_agreement(org)
    invoice, payment, remote = entities(a)
    apply_invoice(a, invoice, payment)
    remote["status"] = "pending"
    with patch("apps.subscriptions.recurring.gateway", side_effect=provider(a, invoice, payment, remote)):
        reconcile_agreement(a.pk)
    sub.refresh_from_db()
    assert sub.is_valid


def test_durable_webhook_recovers_after_provider_outage_without_double_grant(billing):
    from apps.subscriptions.tasks import process_payment_webhook
    org, sub, _ = billing
    agreement = make_agreement(org)
    invoice, payment, remote = entities(agreement)
    event = PaymentWebhookEvent.objects.create(event_id="recurring:recovery", event_type="subscription.charged",
        payload={"account_scope": account_scope(), "subscription_id": agreement.provider_id, "event_type": "subscription.charged"})
    with patch("apps.subscriptions.recurring.gateway", side_effect=PaymentUnavailable("Unavailable")):
        process_payment_webhook(str(event.pk))
    event.refresh_from_db()
    assert not event.is_processed and event.attempts == 1
    assert not RecurringCharge.objects.exists()
    with patch("apps.subscriptions.recurring.gateway", side_effect=provider(agreement, invoice, payment, remote)):
        process_payment_webhook(str(event.pk))
        process_payment_webhook(str(event.pk))
    event.refresh_from_db()
    sub.refresh_from_db()
    assert event.is_processed and event.attempts == 2 and not event.last_error
    assert sub.is_valid and sub.plan.code == "starter"
    assert RecurringCharge.objects.count() == 1


def test_broker_outage_preserves_webhook_inbox(billing):
    from apps.subscriptions.tasks import enqueue_webhook
    event = PaymentWebhookEvent.objects.create(event_id="recurring:broker", event_type="subscription.charged", payload={})
    with patch("apps.subscriptions.tasks.process_payment_webhook.delay", side_effect=ConnectionError("offline")):
        enqueue_webhook(str(event.pk))
    event.refresh_from_db()
    assert not event.is_processed
