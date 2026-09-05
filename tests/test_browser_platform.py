"""Real Chromium + Vite + Django test database; only outbound Meta is mocked.

Opt in with V4_BROWSER_TESTS=1. Install frontend deps and Playwright Chromium first.
"""
import os
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
from rest_framework.authtoken.models import Token
from tests.test_messaging_platform import workspace, inbound
from apps.leads.capture import capture_message_lead


@pytest.mark.skipif(os.environ.get("V4_BROWSER_TESTS") != "1", reason="Opt-in real browser test")
@pytest.mark.django_db(transaction=True)
def test_browser_inbox_and_automation(workspace, live_server):
    for channel, name in [("INSTAGRAM", "Instagram Browser Customer"), ("WHATSAPP", "WhatsApp Browser Customer")]:
        message = inbound(workspace, channel=channel, mid=f"browser-{channel}")
        message.conversation.customer.display_name = name
        message.conversation.customer.save()
        capture_message_lead(message)
    token = Token.objects.create(user=workspace.owner)
    env = {**os.environ, "V4_BACKEND_URL": live_server.url, "V4_TEST_TOKEN": token.key, "V4_TEST_ORG": str(workspace.pk)}
    with patch("apps.conversations.outbound.enqueue_dispatch"):
        result = subprocess.run(["node", "tests/browser-platform.cjs"], cwd=Path(__file__).resolve().parent.parent / "frontend", env=env, capture_output=True, text=True, encoding="utf8", timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(os.environ.get("V4_BROWSER_TESTS") != "1", reason="Opt-in real browser test")
@pytest.mark.parametrize("scenario", ["free", "expired", "unavailable"])
@pytest.mark.django_db(transaction=True)
def test_browser_automation_plan_access(workspace, live_server, scenario):
    from apps.automations.models import Automation
    from apps.subscriptions.models import Plan, Subscription
    from tests.test_messaging_platform import client

    subscription = workspace.subscription
    if scenario == "expired":
        subscription.status = Subscription.Status.EXPIRED
    else:
        subscription.plan = Plan.objects.get(code=Plan.Code.FREE)
    subscription.save()
    token = Token.objects.create(user=workspace.owner)
    env = {**os.environ, "V4_BACKEND_URL": live_server.url, "V4_TEST_TOKEN": token.key,
           "V4_TEST_ORG": str(workspace.pk), "V4_AUTOMATION_ACCESS_CASE": scenario}
    result = subprocess.run(
        ["node", "tests/browser-automation-access.cjs"],
        cwd=Path(__file__).resolve().parent.parent / "frontend", env=env,
        capture_output=True, text=True, encoding="utf8", timeout=150,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rule = Automation.objects.get(organization=workspace, name="Plan access draft")
    assert rule.enabled is False
    # UI guidance does not replace the server's entitlement enforcement.
    response = client(workspace).patch(f"/api/v1/automations/{rule.pk}/", {"enabled": True}, format="json")
    assert response.status_code == 400
    rule.refresh_from_db()
    assert rule.enabled is False


@pytest.mark.skipif(os.environ.get("V4_BROWSER_TESTS") != "1", reason="Opt-in real browser test")
@pytest.mark.django_db(transaction=True)
def test_browser_starter_addon_checkout(workspace, live_server, settings):
    import hashlib
    import hmac
    from tests.test_automation_billing import starter
    from apps.automations.models import Automation
    from apps.subscriptions.models import Subscription
    starter(workspace)
    settings.RAZORPAY_KEY_ID = "rzp_test_browser"
    settings.RAZORPAY_KEY_SECRET = "browser-secret"
    token = Token.objects.create(user=workspace.owner)
    signature = hmac.new(b"browser-secret", b"pay_browser|sub_browser", hashlib.sha256).hexdigest()
    env = {**os.environ, "V4_BACKEND_URL": live_server.url, "V4_TEST_TOKEN": token.key,
           "V4_TEST_ORG": str(workspace.pk), "V4_PAYMENT_SIGNATURE": signature}
    def gateway(method, path, payload=None):
        from django.utils import timezone
        start = int(timezone.now().timestamp()) - 30
        plan = {"id": "plan_browser", "period": "monthly", "interval": 1, "item": {"amount": 39900, "currency": "INR"}}
        if path in ("plans", "plans/plan_browser"): return plan
        if path in ("subscriptions", "subscriptions/sub_browser"):
            return {"id": "sub_browser", "plan_id": "plan_browser", "quantity": 1, "status": "created" if method == "POST" else "active", "current_start": start, "current_end": start + 2592000, "paid_count": 1}
        if path.startswith("invoices?"):
            return {"items": [{"id": "inv_browser", "subscription_id": "sub_browser", "payment_id": "pay_browser", "order_id": "order_browser", "status": "paid", "amount": 39900, "amount_paid": 39900, "currency": "INR", "billing_start": start, "billing_end": start + 2592000, "paid_at": start}]}
        if path == "payments/pay_browser": return {"id": "pay_browser", "invoice_id": "inv_browser", "order_id": "order_browser", "amount": 39900, "currency": "INR", "status": "captured", "created_at": start}
        raise AssertionError((method, path))
    with patch("apps.subscriptions.recurring.gateway", side_effect=gateway):
        result = subprocess.run(["node", "tests/browser-automation-addon.cjs"],
            cwd=Path(__file__).resolve().parent.parent / "frontend", env=env,
            capture_output=True, text=True, encoding="utf8", timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
    assert Subscription.objects.get(organization=workspace).automation_entitled
    assert Automation.objects.get(organization=workspace, name="Starter auto reply").enabled

