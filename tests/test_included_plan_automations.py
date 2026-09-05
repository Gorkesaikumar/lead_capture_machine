from decimal import Decimal
from unittest.mock import patch
import pytest
from tests.test_messaging_platform import workspace, client, inbound
from apps.automations.models import Automation, AutomationAction, AutomationExecution
from apps.automations.services import evaluate_message
from apps.subscriptions.models import Plan


@pytest.mark.django_db
@pytest.mark.parametrize("code,price", [("creator", "1500.00"), ("enterprise", "8000.00")])
def test_plan_includes_live_automation_without_addon(workspace, code, price):
    subscription = workspace.subscription
    subscription.plan = Plan.objects.get(code=code)
    subscription.automation_addon_start = None
    subscription.automation_addon_end = None
    subscription.save()
    api = client(workspace)
    plans = api.get("/api/v1/subscriptions/plans/").data["plans"]
    plan = next(item for item in plans if item["code"] == code)
    assert Decimal(plan["price_inr"]) == Decimal(price)
    assert "DM Automation included (no add-on required)" in plan["features"]
    access = api.get("/api/v1/subscriptions/current/").data["automation"]
    assert access["included"] and access["entitled"]
    assert not access["addon_available"]

    rule = Automation.objects.create(organization=workspace, name="Included reply", channel="INSTAGRAM", trigger_type="INCOMING")
    AutomationAction.objects.create(automation=rule, action_type="SEND_REPLY", configuration={"text": "Thanks for contacting us."})
    assert api.patch(f"/api/v1/automations/{rule.pk}/", {"enabled": True}, format="json").status_code == 200
    with patch("apps.conversations.outbound.enqueue_dispatch"):
        evaluate_message(inbound(workspace))
    execution = AutomationExecution.objects.get(automation=rule)
    assert execution.status == "QUEUED"
    assert execution.conversation.messages.filter(direction="OUTBOUND").count() == 1
