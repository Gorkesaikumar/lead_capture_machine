"""Regression tests for boundary conditions found in the final audit."""
import re
from datetime import timedelta
from unittest.mock import patch
import pytest
from django.core import mail, signing
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.conversations.models import Message
from apps.conversations.services import ConversationService
from apps.conversations.outbound import queue_message, dispatch_message
from apps.integrations.meta.base import OutboundResult
from apps.integrations.models import DataDeletionRequest
from apps.integrations.deletion import delete_instagram_data
from apps.leads.capture import capture_message_lead
from apps.leads.models import LeadForm
from apps.automations.models import Automation, AutomationAction, AutomationExecution
from apps.automations.services import evaluate_message
from tests.test_messaging_platform import workspace, inbound, client

pytestmark = pytest.mark.django_db


def test_early_read_receipt_is_reconciled_after_provider_acceptance(workspace):
    incoming = inbound(workspace)
    outgoing = queue_message(incoming.conversation, {"text": "Reply"}, dispatch=False)
    def send(*args):
        ConversationService.update_message_delivery_status("early-read", "READ", organization=workspace, channel="INSTAGRAM")
        return OutboundResult(success=True, external_message_id="early-read")
    with patch("apps.conversations.outbound.InstagramMessagingProvider.send_text_message", side_effect=send):
        assert dispatch_message(outgoing.pk).delivery_status == "READ"


def test_conditions_observe_prior_rule_updates(workspace):
    message = inbound(workspace)
    capture_message_lead(message)
    first = Automation.objects.create(organization=workspace, name="Tag", channel="INSTAGRAM", trigger_type="INCOMING", priority=1, enabled=True)
    AutomationAction.objects.create(automation=first, action_type="ADD_TAG", action_order=0, configuration={"tag": "Qualified"})
    second = Automation.objects.create(organization=workspace, name="Qualified", channel="INSTAGRAM", trigger_type="INCOMING", priority=2, enabled=True, conditions={"has_tag": "Qualified"})
    AutomationAction.objects.create(automation=second, action_type="CHANGE_STATUS", action_order=0, configuration={"status": "QUALIFIED"})
    evaluate_message(message)
    assert AutomationExecution.objects.count() == 2
    assert message.conversation.lead.status == "QUALIFIED"


@pytest.mark.parametrize("conditions", [{"lead_status": "LOST"}, {"has_tag": "missing"}, {"message_type": "IMAGE"}, {"unassigned": False}])
def test_unmet_conditions_have_no_side_effects(workspace, conditions):
    message = inbound(workspace)
    capture_message_lead(message)
    rule = Automation.objects.create(organization=workspace, name="Blocked", channel="INSTAGRAM", trigger_type="INCOMING", enabled=True, conditions=conditions)
    AutomationAction.objects.create(automation=rule, action_type="SEND_REPLY", action_order=0, configuration={"text": "Must not send"})
    evaluate_message(message)
    assert not AutomationExecution.objects.exists()
    assert not Message.objects.filter(direction="OUTBOUND").exists()


def test_password_reset_is_single_use_and_revokes_tokens(workspace):
    token = Token.objects.create(user=workspace.owner)
    anonymous = APIClient()
    response = anonymous.post("/api/v1/auth/password/reset/", {"email": workspace.owner.email})
    assert response.status_code == 200
    reset = re.search(r"token=([^\s]+)", mail.outbox[-1].body).group(1)
    from urllib.parse import unquote
    data = {"token": unquote(reset), "password": "DifferentSecurePassword!78"}
    assert anonymous.post("/api/v1/auth/password/reset/confirm/", data).status_code == 200
    assert not Token.objects.filter(pk=token.pk).exists()
    assert anonymous.post("/api/v1/auth/password/reset/confirm/", data).status_code == 400


def test_email_verification_cannot_be_used_after_address_change(workspace):
    token = signing.dumps({"user": str(workspace.owner.pk), "email": workspace.owner.email}, salt="email-verification")
    assert APIClient().post("/api/v1/auth/email/verify/", {"token": token}).status_code == 200
    workspace.owner.refresh_from_db()
    assert workspace.owner.email_verified_at is not None
    workspace.owner.email = "new@example.test"
    workspace.owner.save()
    assert APIClient().post("/api/v1/auth/email/verify/", {"token": token}).status_code == 400


@pytest.mark.parametrize("patch_data", [{"email": "not-email"}, {"password": "12345678"}, {"name": {"bad": "type"}}])
def test_signup_validates_before_writing(patch_data):
    data = {"name": "New Owner", "email": "owner@example.test", "password": "NontrivialSecret!19", "organization": "New Studio", **patch_data}
    assert APIClient().post("/api/v1/auth/signup/", data, format="json").status_code == 400
    assert not User.objects.filter(email="owner@example.test").exists()


def test_public_form_cors_does_not_open_private_api(workspace):
    form = LeadForm.objects.create(organization=workspace, name="Website")
    c = APIClient()
    origin = "https://photography.example.test"
    path = f"/api/v1/forms/{form.public_id}/submit/"
    preflight = c.options(path, HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST", HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type")
    assert preflight["Access-Control-Allow-Origin"] == origin
    private = c.options("/api/v1/leads/", HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET")
    assert "Access-Control-Allow-Origin" not in private
    response = c.post(path, {"name": "Website Customer", "email": "customer@example.test", "message": "A portrait inquiry"}, HTTP_ORIGIN=origin)
    assert response.status_code == 201
    assert Message.objects.get().conversation.channel == "WEBSITE"


def test_patch_status_uses_lifecycle_and_logs_activity(workspace):
    lead, _ = capture_message_lead(inbound(workspace))
    response = client(workspace).patch(f"/api/v1/leads/{lead.pk}/", {"status": "QUALIFIED"}, format="json")
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.qualified_at is not None
    assert lead.activities.filter(activity_type="STATUS_CHANGED").exists()


def test_deletion_removes_instagram_data_preserves_whatsapp(workspace):
    instagram = inbound(workspace)
    capture_message_lead(instagram)
    whatsapp = inbound(workspace, channel="WHATSAPP", mid="preserved")
    capture_message_lead(whatsapp)
    receipt = DataDeletionRequest.objects.create(scopes=[{"organization": str(workspace.pk), "account": "90001"}])
    delete_instagram_data(str(receipt.pk))
    receipt.refresh_from_db()
    assert receipt.status == "COMPLETED" and receipt.scopes == []
    assert not Message.objects.filter(conversation__channel="INSTAGRAM").exists()
    assert Message.objects.filter(pk=whatsapp.pk).exists()


def test_whatsapp_embedded_signup_requires_configuration_and_bound_state(workspace, settings):
    settings.META_WHATSAPP_CONFIG_ID = "test-configuration"
    start = client(workspace).get("/api/v1/integrations/oauth/whatsapp/login/")
    assert start.status_code == 200
    assert start.data["config_id"] == "test-configuration"
    assert "business_management" not in str(start.data)
    from apps.integrations.connection_service import consume_attempt, OAuthFailure
    consume_attempt(start.data["state"], "WHATSAPP", workspace.owner, workspace)
    with pytest.raises(OAuthFailure):
        consume_attempt(start.data["state"], "WHATSAPP", workspace.owner, workspace)


def test_manual_lead_creation_saves_status_and_assignment_atomically(workspace):
    data = {"customer_name": "Manual Customer", "email": "manual@example.test", "status": "QUALIFIED", "assigned_staff_id": str(workspace.owner.pk)}
    response = client(workspace).post("/api/v1/leads/", data, format="json")
    assert response.status_code == 201
    assert response.data["assigned_staff"]["id"] == str(workspace.owner.pk)
    assert response.data["status"] == "QUALIFIED"
    assert response.data["qualified_at"]


def test_foreign_assignee_does_not_create_partial_lead(workspace):
    other = User.objects.create_user(email="outsider@example.test", password="StrongSecret88!")
    data = {"customer_name": "Should not exist", "email": "partial@example.test", "assigned_staff_id": str(other.pk)}
    response = client(workspace).post("/api/v1/leads/", data, format="json")
    assert response.status_code == 400
    from apps.customers.models import Customer
    assert not Customer.objects.filter(email="partial@example.test").exists()
