"""Acceptance tests for tenant isolation, webhooks, the outbox and automation.
All external HTTP is mocked. No production credentials are used.
"""
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.services import SubscriptionEntitlementService
from apps.integrations.models import IntegrationConfig, RawWebhookEvent
from apps.integrations.meta.base import OutboundResult
from apps.integrations.pipeline import InboundPipelineService
from apps.core.utils.crypto import encrypt_string
from apps.conversations.models import Message, Conversation
from apps.conversations.services import ConversationService
from apps.conversations.outbound import queue_message, dispatch_message, MessagingUnavailable
from apps.leads.models import Lead, LeadTrigger
from apps.automations.models import Automation, AutomationAction, AutomationExecution
from apps.automations.services import evaluate_message, matches

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace():
    user = User.objects.create_user(email="platform@example.test", password="StrongPass8!", full_name="Owner")
    org = Organization.objects.create(name="Studio A", slug="studio-a", owner=user)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    SubscriptionEntitlementService.seed_default_plans()
    Subscription.objects.create(organization=org, plan=Plan.objects.get(code=Plan.Code.ENTERPRISE), status=Subscription.Status.ACTIVE, current_period_start=timezone.now(), current_period_end=timezone.now()+timedelta(days=30))
    for channel in ("INSTAGRAM", "WHATSAPP"):
        IntegrationConfig.objects.create(organization=org, provider=channel, credentials={"access_token": encrypt_string("test-token")}, metadata={"destination_id": "90001" if channel == "INSTAGRAM" else "90002"})
    return org


def inbound(org, channel="INSTAGRAM", mid="inbound-1", sender="123456789012345", text="price", when=None):
    return ConversationService.store_inbound_message({"channel": channel, "external_user_id": sender, "external_message_id": mid, "text": text, "provider_timestamp": when or timezone.now()}, organization=org)[0]


def client(org):
    c = APIClient()
    c.force_authenticate(org.owner)
    c.credentials(HTTP_X_ORGANIZATION_ID=str(org.pk))
    return c


def payload(channel, mid="webhook-1", text="price"):
    now = int(timezone.now().timestamp())
    if channel == "INSTAGRAM":
        return {"object": "instagram", "entry": [{"id": "90001", "messaging": [{"sender": {"id": "123456789012345"}, "recipient": {"id": "90001"}, "timestamp": now*1000, "message": {"mid": mid, "text": text}}]}]}
    return {"object": "whatsapp_business_account", "entry": [{"id": "waba-test", "changes": [{"field": "messages", "value": {"metadata": {"phone_number_id": "90002"}, "messages": [{"id": mid, "from": "123456789012345", "timestamp": str(now), "type": "text", "text": {"body": text}}]}}]}]}


def receive(data, channel):
    body = json.dumps(data).encode()
    signature = "sha256="+hmac.new(settings.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return APIClient().post(f"/api/v1/webhooks/meta/{channel.lower()}/", body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature)


@pytest.mark.parametrize("channel", ["INSTAGRAM", "WHATSAPP"])
@pytest.mark.parametrize("trigger", ["EXACT", "NEW_LEAD", "NEW_CONVERSATION"])
def test_complete_inbound_capture_automation_outbound(workspace, channel, trigger, django_capture_on_commit_callbacks):
    if channel == "INSTAGRAM":
        # Instagram now requires keyword intent before NEW_LEAD/tag/status automations.
        LeadTrigger.objects.create(organization=workspace, phrase="price", match_type="CONTAINS")
    rule = Automation.objects.create(organization=workspace, name="Pricing", channel=channel, trigger_type=trigger, trigger_value="price", enabled=True)
    AutomationAction.objects.create(automation=rule, action_type="ADD_TAG", action_order=0, configuration={"tag": "Pricing"})
    AutomationAction.objects.create(automation=rule, action_type="CHANGE_STATUS", action_order=1, configuration={"status": "QUALIFIED"})
    AutomationAction.objects.create(automation=rule, action_type="SEND_REPLY", action_order=2, configuration={"text": "Our packages start here."})
    with patch("apps.conversations.outbound.enqueue_dispatch"), django_capture_on_commit_callbacks(execute=True):
        response = receive(payload(channel), channel)
    assert response.status_code == 200
    incoming = Message.objects.get(direction="INBOUND")
    assert incoming.conversation.lead.tags == ["Pricing"]
    assert incoming.conversation.lead.status == "QUALIFIED"
    assert incoming.conversation.unread_count == 1
    outgoing = Message.objects.get(direction="OUTBOUND")
    assert outgoing.delivery_status == "QUEUED"
    provider = "InstagramMessagingProvider" if channel == "INSTAGRAM" else "WhatsAppMessagingProvider"
    with patch(f"apps.conversations.outbound.{provider}.send_text_message", return_value=OutboundResult(success=True, external_message_id="accepted-by-meta")) as send:
        assert dispatch_message(outgoing.pk).delivery_status == "SENT"
        assert dispatch_message(outgoing.pk).delivery_status == "SENT"
        send.assert_called_once()
    assert receive(payload(channel), channel).status_code == 200
    assert Message.objects.count() == 2
    assert Lead.objects.count() == 1
    assert AutomationExecution.objects.count() == 1
    if trigger in ("NEW_LEAD", "NEW_CONVERSATION"):
        assert receive(payload(channel, mid="second-message"), channel).status_code == 200
        assert AutomationExecution.objects.count() == 1


def test_pending_duplicate_does_not_discard_event(workspace):
    data = payload("INSTAGRAM")
    event, created = InboundPipelineService.record_raw_event("INSTAGRAM", b"", "", data)
    repeated, created = InboundPipelineService.record_raw_event("INSTAGRAM", b"", "", data)
    event.refresh_from_db()
    assert event.status == "PENDING" and not created
    assert InboundPipelineService.process_raw_webhook_event(event)["new_messages_created"] == 1


def test_batch_hash_includes_every_message(workspace):
    a = payload("INSTAGRAM")
    b = payload("INSTAGRAM")
    b["entry"][0]["messaging"].append(payload("INSTAGRAM", "second")["entry"][0]["messaging"][0])
    assert InboundPipelineService.generate_event_id(a) != InboundPipelineService.generate_event_id(b)
    assert receive(a, "INSTAGRAM").status_code == 200
    assert receive(b, "INSTAGRAM").status_code == 200
    assert Message.objects.filter(direction="INBOUND").count() == 2


@pytest.mark.parametrize("data", [[], None, {"entry": [42]}, {"entry": "invalid"}])
def test_invalid_webhook_shape_rejected(workspace, data):
    assert receive(data, "INSTAGRAM").status_code == 400


def test_invalid_signature_and_challenge(workspace):
    c = APIClient()
    assert c.post("/api/v1/webhooks/meta/instagram/", {}, format="json").status_code == 403
    assert c.get("/api/v1/webhooks/meta/instagram/", {"hub.mode": "subscribe", "hub.verify_token": settings.META_VERIFY_TOKEN, "hub.challenge": "challenge"}).content == b"challenge"
    assert c.get("/api/v1/webhooks/meta/instagram/", {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "challenge"}).status_code == 403


def test_queue_failure_retains_webhook_for_retry(workspace):
    with patch("apps.integrations.views.process_instagram_webhook_event_task.apply", side_effect=RuntimeError("offline")):
        assert receive(payload("INSTAGRAM"), "INSTAGRAM").status_code == 503
    assert RawWebhookEvent.objects.get().status == "PENDING"


def test_same_external_identity_across_workspaces(workspace):
    other = Organization.objects.create(name="Studio B", slug="studio-b", owner=workspace.owner)
    first, second = inbound(workspace), inbound(other)
    assert first.conversation.customer_id != second.conversation.customer_id
    assert first.pk != second.pk


@pytest.mark.parametrize("url", ["leads/", "conversations/", "automations/", "automations/history/", "integrations/health/", "bookings/", "notifications/", "audit/"])
def test_anonymous_denied(workspace, url):
    assert APIClient().get("/api/v1/"+url).status_code in (401, 403)


def test_cross_workspace_reads_and_send_blocked(workspace):
    other_user = User.objects.create_user(email="other@example.test", password="StrongPass8!")
    other = Organization.objects.create(name="Other", slug="other", owner=other_user)
    message = inbound(other)
    c = client(workspace)
    assert c.get(f"/api/v1/conversations/{message.conversation_id}/").status_code == 404
    assert c.post(f"/api/v1/conversations/{message.conversation_id}/send/", {"text": "hello"}).status_code == 404
    c.credentials(HTTP_X_ORGANIZATION_ID=str(other.pk))
    assert c.get("/api/v1/conversations/").status_code == 403
    assert c.get("/api/v1/integrations/health/").status_code == 403


def test_malformed_workspace_header_denied(workspace):
    c = client(workspace)
    c.credentials(HTTP_X_ORGANIZATION_ID="not-a-uuid")
    assert c.get("/api/v1/conversations/").status_code == 403


@pytest.mark.parametrize("channel", ["INSTAGRAM", "WHATSAPP"])
def test_window_and_send_idempotency(workspace, channel):
    message = inbound(workspace, channel)
    c = message.conversation
    first = queue_message(c, {"text": "Hi"}, request_id="stable", dispatch=False)
    second = queue_message(c, {"text": "Hi"}, request_id="stable", dispatch=False)
    assert first.pk == second.pk
    message.provider_timestamp = timezone.now()-timedelta(hours=25)
    message.save()
    with pytest.raises(MessagingUnavailable):
        queue_message(c, {"text": "Late"}, dispatch=False)


def test_whatsapp_template_outside_window(workspace):
    msg = inbound(workspace, "WHATSAPP", when=timezone.now()-timedelta(days=2))
    sent = queue_message(msg.conversation, {"template": {"name": "approved_greeting", "language": "en_US"}}, dispatch=False)
    with patch("apps.conversations.outbound.WhatsAppMessagingProvider.send_template_message", return_value=OutboundResult(True, "template-id")) as provider:
        assert dispatch_message(sent.pk).delivery_status == "SENT"
        provider.assert_called_once()


@pytest.mark.parametrize("result,code", [(OutboundResult(False, error_message="Meta API error (190): expired"), "token_expired"), (OutboundResult(False, error_message="Missing permission"), "permission_required"), (OutboundResult(False, error_message="Network timeout"), "delivery_unconfirmed"), (OutboundResult(True), "provider_rejected")])
def test_send_failures_never_claim_success(workspace, result, code):
    msg = queue_message(inbound(workspace).conversation, {"text": "Hi"}, dispatch=False)
    with patch("apps.conversations.outbound.InstagramMessagingProvider.send_text_message", return_value=result):
        failed = dispatch_message(msg.pk)
    assert failed.delivery_status == "FAILED"
    assert failed.error_code == code
    assert failed.external_message_id == ""


def test_delivery_status_monotonic_and_scoped(workspace):
    conv = inbound(workspace, "WHATSAPP").conversation
    msg = Message.objects.create(conversation=conv, direction="OUTBOUND", delivery_status="SENT", external_message_id="out-1")
    ConversationService.update_message_delivery_status("out-1", "read", organization=workspace, channel="WHATSAPP")
    ConversationService.update_message_delivery_status("out-1", "sent", organization=workspace, channel="WHATSAPP")
    ConversationService.update_message_delivery_status("out-1", "failed", organization=workspace, channel="WHATSAPP")
    msg.refresh_from_db()
    assert msg.delivery_status == "READ"
    assert ConversationService.update_message_delivery_status("out-1", "unknown", organization=workspace, channel="WHATSAPP") is None


def test_older_message_preserves_latest_preview(workspace):
    msg = inbound(workspace, text="Latest")
    inbound(workspace, mid="older", text="Old", when=timezone.now()-timedelta(days=2))
    msg.conversation.refresh_from_db()
    assert msg.conversation.last_message_preview == "Latest"
    assert msg.conversation.unread_count == 2
    msg.conversation.mark_read()
    assert msg.conversation.messages.filter(is_read=False).count() == 0


@pytest.mark.parametrize("trigger,text,value,first,expected", [("EXACT", " PRICE ", "price", False, True), ("EXACT", "pricing", "price", False, False), ("CONTAINS", "show price please", "price", False, True), ("FIRST_INTERACTION", "hi", "", True, True), ("FIRST_INTERACTION", "hi", "", False, False), ("INCOMING", "", "", False, True)])
def test_trigger_matching(trigger, text, value, first, expected):
    rule = Automation(trigger_type=trigger, trigger_value=value, conditions={})
    assert matches(rule, text, first=first) is expected


def test_automation_crud_preview_disabled_and_isolation(workspace):
    c = client(workspace)
    data = {"name": "Demo", "channel": "INSTAGRAM", "trigger_type": "CONTAINS", "trigger_value": "demo", "conditions": {}, "enabled": False, "actions": [{"action_type": "ADD_TAG", "action_order": 0, "configuration": {"tag": "Demo"}}]}
    res = c.post("/api/v1/automations/", data, format="json")
    assert res.status_code == 201, res.data
    rule_id = res.data["id"]
    assert c.post(f"/api/v1/automations/{rule_id}/test/", {"text": "demo"}, format="json").data["matched"]
    msg = inbound(workspace, text="demo")
    evaluate_message(msg)
    assert not AutomationExecution.objects.exists()
    assert c.patch(f"/api/v1/automations/{rule_id}/", {"enabled": True}, format="json").status_code == 200
    evaluate_message(msg)
    evaluate_message(msg)
    assert AutomationExecution.objects.count() == 1
    assert c.delete(f"/api/v1/automations/{rule_id}/").status_code == 204
    assert AutomationExecution.objects.get().automation_id is None


def test_health_is_unverified_and_does_not_expose_credentials(workspace):
    data = client(workspace).get("/api/v1/integrations/health/").data
    assert data["instagram"]["connection_status"] == "CONFIGURED_UNVERIFIED"
    assert "test-token" not in json.dumps(data)


def test_api_send_returns_queued_not_external_success(workspace):
    conv = inbound(workspace).conversation
    res = client(workspace).post(f"/api/v1/conversations/{conv.pk}/send/", {"text": "Hello", "request_id": "req-1"})
    assert res.status_code == 202, res.data
    assert res.data["delivery_status"] == "QUEUED"
    assert res.data["external_message_id"] == ""
