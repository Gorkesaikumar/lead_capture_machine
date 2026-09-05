import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from tests.test_messaging_platform import workspace, client, inbound
from apps.automations.models import Automation, AutomationAction, AutomationUsage, AutomationExecution
from apps.automations.services import evaluate_message
from apps.automations.usage import next_month
from apps.subscriptions.models import Plan, Subscription, BillingTransaction
from apps.subscriptions.payments import create_order, apply_capture

pytestmark = pytest.mark.django_db


def starter(org, paid=False):
    sub = org.subscription
    sub.plan = Plan.objects.get(code="starter")
    if paid:
        sub.automation_addon_start = timezone.now()-timedelta(minutes=1)
        sub.automation_addon_end = next_month(sub.automation_addon_start)
    sub.save()
    return sub


def rule(org, name="Pricing"):
    obj = Automation.objects.create(organization=org, name=name, channel="INSTAGRAM", trigger_type="INCOMING", enabled=True)
    AutomationAction.objects.create(automation=obj, action_type="SEND_REPLY", action_order=0, configuration={"text": "Thanks!"})
    return obj


@pytest.fixture
def gateway_settings(settings):
    settings.RAZORPAY_KEY_ID = "rzp_test_unit"
    settings.RAZORPAY_KEY_SECRET = "unit-secret"
    settings.RAZORPAY_WEBHOOK_SECRET = "webhook-secret"
    return settings


def signed_payment(order_id="order_automation", **changes):
    return {"id": "pay_automation", "order_id": order_id, "status": "captured", "amount": 39900, "currency": "INR", **changes}


def checkout(org):
    with patch("apps.subscriptions.payments.gateway", return_value={"id": "order_automation", "amount": 39900, "currency": "INR"}) as gateway:
        order = create_order(org, product="dm_automation")
        assert gateway.call_args.args[2]["amount"] == 39900
    return order


def test_starter_addon_is_separate_from_base_price(workspace):
    sub = starter(workspace)
    assert sub.plan.price_inr == Decimal("400.00")
    assert sub.plan.automation_run_limit == 1000
    assert not sub.automation_entitled
    data = client(workspace).get("/api/v1/subscriptions/current/").data
    assert data["automation"]["addon_price_inr"] == "399.00"
    assert data["automation"]["addon_available"] and data["automation"]["can_manage_billing"]
    assert data["automation"]["meta_fees_included"] is False
    assert data["automation"]["auto_renews"] is False


@pytest.mark.parametrize("state", ["paid", "expired_addon", "expired_plan", "pending", "free", "included"])
def test_effective_automation_entitlement(workspace, state):
    sub = starter(workspace, paid=True)
    if state == "expired_addon": sub.automation_addon_end = timezone.now()-timedelta(seconds=1)
    if state == "expired_plan": sub.current_period_end = timezone.now()-timedelta(seconds=1)
    if state == "pending": sub.status = "pending"
    if state in ("free", "included"): sub.plan = Plan.objects.get(code="free" if state == "free" else "creator")
    sub.save()
    assert sub.automation_entitled is (state in ("paid", "included"))
    assert workspace.has_feature("can_use_automations") is (state in ("paid", "included"))


def test_starter_can_enable_only_with_paid_addon(workspace):
    sub = starter(workspace)
    obj = rule(workspace)
    obj.enabled = False
    obj.save()
    url = f"/api/v1/automations/{obj.pk}/"
    assert client(workspace).patch(url, {"enabled": True}, format="json").status_code == 400
    sub.automation_addon_start = timezone.now()
    sub.automation_addon_end = next_month(sub.automation_addon_start)
    sub.save()
    assert client(workspace).patch(url, {"enabled": True}, format="json").status_code == 200


def test_run_limit_duplicate_and_new_paid_period(workspace):
    sub = starter(workspace, paid=True)
    usage = AutomationUsage.objects.create(organization=workspace, period_start=sub.automation_addon_start,
        period_end=sub.automation_addon_end, runs_started=999)
    obj = rule(workspace)
    msg = inbound(workspace)
    with patch("apps.conversations.outbound.enqueue_dispatch"):
        evaluate_message(msg)
        evaluate_message(msg)
        evaluate_message(inbound(workspace, mid="second"))
    usage.refresh_from_db()
    assert usage.runs_started == 1000
    assert AutomationExecution.objects.filter(status="BLOCKED", error__contains="Monthly automation limit").count() == 1
    assert msg.conversation.messages.filter(direction="OUTBOUND").count() == 1
    # Deleting history/rules cannot restore consumed usage.
    obj.delete()
    assert AutomationUsage.objects.get(pk=usage.pk).runs_started == 1000
    sub.automation_addon_start = timezone.now()
    sub.automation_addon_end = next_month(sub.automation_addon_start)
    sub.save()
    rule(workspace, "Next period")
    with patch("apps.conversations.outbound.enqueue_dispatch"):
        evaluate_message(inbound(workspace, mid="next-period"))
    assert AutomationUsage.objects.get(period_start=sub.automation_addon_start).runs_started == 1


def test_multiple_actions_count_as_one_run_and_preview_is_free(workspace):
    starter(workspace, paid=True)
    obj = rule(workspace)
    AutomationAction.objects.create(automation=obj, action_type="SEND_REPLY", action_order=1, configuration={"text": "One more detail"})
    response = client(workspace).post(f"/api/v1/automations/{obj.pk}/test/", {"text": "hello"}, format="json")
    assert response.status_code == 200
    assert not AutomationUsage.objects.exists()
    with patch("apps.conversations.outbound.enqueue_dispatch"):
        evaluate_message(inbound(workspace))
    assert AutomationUsage.objects.get().runs_started == 1


def test_month_end_clamped():
    start = timezone.datetime(2026, 1, 31, 12, tzinfo=timezone.get_current_timezone())
    assert next_month(start).day == 28


def test_missing_payment_config_never_grants_access(workspace, settings):
    starter(workspace)
    settings.RAZORPAY_KEY_ID = ""
    response = client(workspace).post("/api/v1/subscriptions/checkout/", {"product": "dm_automation"}, format="json")
    assert response.status_code == 503
    assert not BillingTransaction.objects.exists()


def test_checkout_reuses_order_and_ignores_client_price(workspace, gateway_settings):
    starter(workspace)
    checkout(workspace)
    with patch("apps.subscriptions.payments.gateway") as gateway:
        response = client(workspace).post("/api/v1/subscriptions/checkout/", {"product": "dm_automation", "amount": 1}, format="json")
    assert response.status_code == 200 and response.data["amount"] == 39900
    gateway.assert_not_called()
    assert BillingTransaction.objects.count() == 1


def test_unpaid_or_forged_verification_cannot_upgrade(workspace, gateway_settings):
    starter(workspace)
    checkout(workspace)
    with patch("apps.subscriptions.payments.gateway") as gateway:
        response = client(workspace).post("/api/v1/subscriptions/verify-payment/", {
            "provider_order_id": "order_automation", "provider_payment_id": "pay_automation", "provider_signature": "fake",
            "plan_code": "enterprise"}, format="json")
    assert response.status_code == 400
    gateway.assert_not_called()
    workspace.subscription.refresh_from_db()
    assert not workspace.subscription.automation_entitled
    assert workspace.subscription.plan.code == "starter"


@pytest.mark.parametrize("changes", [{"amount": 1}, {"currency": "USD"}, {"status": "authorized"}, {"order_id": "order_wrong"}])
def test_capture_requires_exact_order_and_amount(workspace, gateway_settings, changes):
    starter(workspace)
    checkout(workspace)
    with pytest.raises(Exception, match="not captured"):
        apply_capture(BillingTransaction.objects.get().pk, signed_payment(**changes))
    assert not Subscription.objects.get(organization=workspace).automation_entitled


def test_verified_payment_and_duplicate_webhook_grant_once(workspace, gateway_settings):
    starter(workspace)
    checkout(workspace)
    signature = hmac.new(b"unit-secret", b"order_automation|pay_automation", hashlib.sha256).hexdigest()
    with patch("apps.subscriptions.payments.gateway", return_value=signed_payment()):
        response = client(workspace).post("/api/v1/subscriptions/verify-payment/", {
            "provider_order_id": "order_automation", "provider_payment_id": "pay_automation", "provider_signature": signature}, format="json")
    assert response.status_code == 200
    sub = Subscription.objects.get(organization=workspace)
    assert sub.automation_entitled and sub.plan.code == "starter"
    end = sub.automation_addon_end
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": signed_payment()}}}).encode()
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    for _ in range(2):
        response = APIClient().post("/api/v1/subscriptions/webhooks/razorpay/", body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature)
        assert response.status_code == 200
    sub.refresh_from_db()
    assert sub.automation_addon_end == end
    assert BillingTransaction.objects.filter(status="success").count() == 1


def test_unsigned_webhook_is_rejected(workspace, gateway_settings):
    response = APIClient().post("/api/v1/subscriptions/webhooks/razorpay/", {"event": "payment.captured"}, format="json")
    assert response.status_code == 403


def test_member_cannot_purchase_or_verify(workspace, gateway_settings):
    membership = workspace.owner.memberships.get(organization=workspace)
    membership.role = "MEMBER"
    membership.save()
    for endpoint in ("checkout", "verify-payment"):
        assert client(workspace).post(f"/api/v1/subscriptions/{endpoint}/", {}, format="json").status_code == 403


def test_verified_base_plan_uses_order_price_not_client_plan(workspace, gateway_settings):
    sub = starter(workspace)
    sub.plan = Plan.objects.get(code="free")
    sub.save()
    with patch("apps.subscriptions.payments.gateway", return_value={"id": "order_starter", "amount": 40000, "currency": "INR"}):
        order = create_order(workspace, plan_code="starter")
    result = apply_capture(BillingTransaction.objects.get().pk, signed_payment(order_id=order["order_id"], amount=40000))
    assert result.plan.code == "starter" and result.charged_amount == Decimal("400.00")
    assert not result.automation_entitled


@pytest.mark.django_db(transaction=True)
def test_concurrent_runs_cannot_exceed_allowance(workspace):
    from concurrent.futures import ThreadPoolExecutor
    from django.db import close_old_connections, connections
    from apps.conversations.models import Message
    sub = starter(workspace, paid=True)
    AutomationUsage.objects.create(organization=workspace, period_start=sub.automation_addon_start,
        period_end=sub.automation_addon_end, runs_started=999)
    rule(workspace)
    ids = [inbound(workspace, mid=f"concurrent-{i}").pk for i in range(2)]
    def run(message_id):
        close_old_connections()
        try:
            evaluate_message(Message.objects.get(pk=message_id))
        finally:
            connections.close_all()
    with patch("apps.conversations.outbound.enqueue_dispatch"), ThreadPoolExecutor(max_workers=2) as workers:
        list(workers.map(run, ids))
    assert AutomationUsage.objects.get().runs_started == 1000
    assert AutomationExecution.objects.filter(status="BLOCKED").count() == 1
    assert Message.objects.filter(direction="OUTBOUND").count() == 1


def test_another_workspace_cannot_claim_payment(workspace, gateway_settings):
    from apps.accounts.models import User
    from apps.organizations.models import Organization, OrganizationMembership
    starter(workspace)
    checkout(workspace)
    user = User.objects.create_user(email="other-billing@example.test", password="Password8!")
    other = Organization.objects.create(name="Other", slug="other-billing", owner=user)
    OrganizationMembership.objects.create(organization=other, user=user, role="OWNER")
    signature = hmac.new(b"unit-secret", b"order_automation|pay_automation", hashlib.sha256).hexdigest()
    with patch("apps.subscriptions.payments.gateway") as gateway:
        response = client(other).post("/api/v1/subscriptions/verify-payment/", {
            "provider_order_id": "order_automation", "provider_payment_id": "pay_automation", "provider_signature": signature}, format="json")
    assert response.status_code == 400
    gateway.assert_not_called()


def test_failed_run_consumes_one_run_but_disabled_rule_does_not(workspace):
    starter(workspace, paid=True)
    obj = rule(workspace)
    old = inbound(workspace, when=timezone.now()-timedelta(hours=25))
    evaluate_message(old)
    assert AutomationUsage.objects.get().runs_started == 1
    assert AutomationExecution.objects.get().status == "BLOCKED"
    obj.enabled = False
    obj.save()
    evaluate_message(inbound(workspace, mid="disabled"))
    assert AutomationUsage.objects.get().runs_started == 1


def test_first_paid_checkout_provisions_base_subscription(workspace, gateway_settings):
    workspace.subscription.delete()
    with patch("apps.subscriptions.payments.gateway", return_value={"id": "order_first", "amount": 40000, "currency": "INR"}):
        create_order(workspace, plan_code="starter")
    result = apply_capture(BillingTransaction.objects.get().pk, signed_payment(order_id="order_first", amount=40000))
    assert result.plan.code == "starter" and result.is_valid
