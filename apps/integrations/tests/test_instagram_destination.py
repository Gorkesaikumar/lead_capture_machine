"""Synthetic protocol fixtures with realistic IDs, not evidence of a live Meta delivery.

Professional account, authenticated profile ID, OAuth subject and customer IGSID
are intentionally distinct. No production payload, token or DM content is used.
"""
import base64
import copy
import hashlib
import hmac
import json
import logging

import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from apps.conversations.models import Conversation, Message
from apps.customers.models import Customer
from apps.integrations.models import IntegrationConfig, RawWebhookEvent
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.pipeline import InboundPipelineService
from apps.integrations.tasks import process_instagram_webhook_event_task
from apps.leads.models import Lead, LeadTrigger
from apps.subscriptions.services import SubscriptionEntitlementService
from tests.tenant_fixtures import make_organization

pytestmark = pytest.mark.django_db
PROFESSIONAL = "17841405962012345"
PROFILE = "72500123456789012"
OAUTH = "91300123456789012"
CUSTOMER = "61400123456789012"
OTHER = "17841405962987654"
ERROR = "Webhook destination is unconfigured or assigned to multiple workspaces."


def dm(shape="messaging", text="I want a baby shoot", recipient=PROFESSIONAL, entry=PROFESSIONAL, suffix="1"):
    mid = base64.b64encode(f"ig_dm_item:1:IGMessageID:340282366841710301244259:synthetic-{suffix}".encode()).decode()
    value = {"sender": {"id": CUSTOMER}, "recipient": {"id": recipient},
        "timestamp": str(int(timezone.now().timestamp()) * 1000), "message": {"mid": mid, "text": text}}
    content = {"messaging": [value]} if shape == "messaging" else {"changes": [{"field": "messages", "value": value}]}
    return {"object": "instagram", "entry": [{"id": entry, **content}]}


def value_of(payload):
    entry = payload["entry"][0]
    return entry["messaging"][0] if "messaging" in entry else entry["changes"][0]["value"]


def record(payload):
    return InboundPipelineService.record_raw_event("INSTAGRAM", json.dumps(payload).encode(), None, payload)[0]


@pytest.fixture
def connected():
    org = make_organization(name="Instagram routing regression")
    SubscriptionEntitlementService.get_or_create_active_subscription(org)
    config = IntegrationConfig.objects.create(organization=org, provider="INSTAGRAM",
        metadata={"destination_id": PROFESSIONAL, "account_id": PROFESSIONAL, "oauth_user_id": OAUTH,
                  "auth_architecture": "instagram_login"})
    trigger = LeadTrigger.objects.create(organization=org, phrase="baby shoot", match_type="CONTAINS")
    return org, config, trigger


@pytest.mark.parametrize("shape", ["messaging", "changes"])
@pytest.mark.parametrize("text", ["baby shoot", "I want a baby shoot", "Baby Shoot please", "need BABY SHOOT package"])
def test_inbound_shapes_match_trigger_and_map_customer_separately(connected, shape, text):
    org, _, trigger = connected
    payload = dm(shape, text)
    normalized = InstagramInboundParser().parse_messages(payload)[0]
    assert normalized.destination_id == PROFESSIONAL and normalized.external_user_id == CUSTOMER
    result = InboundPipelineService.process_raw_webhook_event(record(payload))
    assert result["new_messages_created"] == result["leads_created"] == 1
    message = Message.objects.get()
    assert message.conversation.organization == org
    assert message.conversation.customer.identities.get().external_user_id == CUSTOMER
    assert message.external_message_id == value_of(payload)["message"]["mid"]
    lead = Lead.objects.get()
    assert lead.organization == org and lead.trigger == trigger
    assert message.conversation.lead_id == lead.pk


@pytest.mark.parametrize("metadata", [
    {"account_id": PROFESSIONAL},
    {"destination_id": OTHER, "account_id": PROFESSIONAL},
    {"destination_id": int(PROFESSIONAL)},
    {"destination_id": OTHER, "auth_architecture": "instagram_login", "profile_id": PROFESSIONAL},
])
def test_previously_unconfigured_normalized_destination_resolves_verified_alias(connected, metadata):
    _, config, _ = connected
    config.metadata = metadata
    config.save()
    payload = dm()
    normalized = InstagramInboundParser().parse_messages(payload)[0]
    # Reproduce the exact old lookup: a normalized DM existed but this missed its connection.
    assert not IntegrationConfig.objects.filter(metadata__destination_id=normalized.destination_id).exists()
    result = InboundPipelineService.process_raw_webhook_event(record(payload))
    assert result["leads_created"] == 1


@pytest.mark.parametrize("shape", ["messaging", "changes"])
def test_instagram_entry_identity_resolves_when_recipient_uses_another_id(connected, shape):
    payload = dm(shape, recipient=PROFILE)
    normalized = InstagramInboundParser().parse_messages(payload)[0]
    assert normalized.destination_id == PROFILE
    assert normalized.destination_aliases == (PROFESSIONAL,)
    assert InboundPipelineService.process_raw_webhook_event(record(payload))["leads_created"] == 1


@pytest.mark.parametrize("shape", ["messaging", "changes"])
def test_missing_recipient_uses_instagram_entry_not_sender_or_metadata(connected, shape):
    payload = dm(shape)
    del value_of(payload)["recipient"]
    value_of(payload)["metadata"] = {"account_id": OTHER}
    assert InstagramInboundParser().parse_messages(payload)[0].destination_id == PROFESSIONAL
    assert InboundPipelineService.process_raw_webhook_event(record(payload))["leads_created"] == 1


@pytest.mark.parametrize("text", ["Hello there", "baby shooter", "grandbaby shoot", "portrait package"])
def test_nonmatching_incoming_dm_remains_in_inbox_without_a_lead(connected, text):
    result = InboundPipelineService.process_raw_webhook_event(record(dm(text=text)))
    assert result["new_messages_created"] == 1 and result["leads_created"] == 0
    assert Customer.objects.count() == Conversation.objects.count() == Message.objects.count() == 1
    assert not Lead.objects.exists()


def test_inactive_and_other_workspace_triggers_do_not_capture(connected):
    _, _, trigger = connected
    trigger.is_active = False
    trigger.save()
    LeadTrigger.objects.create(organization=make_organization(), phrase="baby shoot", match_type="CONTAINS")
    assert InboundPipelineService.process_raw_webhook_event(record(dm()))["leads_created"] == 0
    assert Message.objects.count() == 1


def test_raw_event_and_mid_retries_across_envelopes_are_idempotent(connected):
    payload = dm()
    event = record(payload)
    assert InboundPipelineService.process_raw_webhook_event(event)["leads_created"] == 1
    assert record(payload).pk == event.pk
    assert InboundPipelineService.process_raw_webhook_event(event)["is_duplicate"]
    another_envelope = copy.deepcopy(payload)
    another_envelope["entry"][0]["time"] = 1790000000000
    result = InboundPipelineService.process_raw_webhook_event(record(another_envelope))
    assert result["new_messages_created"] == result["leads_created"] == 0
    assert RawWebhookEvent.objects.count() == 2
    assert Customer.objects.count() == Conversation.objects.count() == Message.objects.count() == Lead.objects.count() == 1


@pytest.mark.parametrize("metadata", [
    {"destination_id": CUSTOMER},
    {"oauth_user_id": PROFESSIONAL, "auth_architecture": "instagram_login"},
    {"profile_id": PROFESSIONAL, "auth_architecture": "facebook_login"},
    {"account_id": ""}, {"account_id": None}, {"account_id": True},
    {"account_id": " " + PROFESSIONAL}, {"account_id": [PROFESSIONAL]},
])
def test_sender_and_unverified_or_invalid_aliases_never_route(connected, metadata):
    _, config, _ = connected
    config.metadata = metadata
    config.save()
    with pytest.raises(ValueError, match=ERROR):
        InboundPipelineService.process_raw_webhook_event(record(dm()))
    assert not Message.objects.exists() and not Customer.objects.exists() and not Lead.objects.exists()


@pytest.mark.parametrize("shape", ["messaging", "changes"])
def test_unknown_destination_never_uses_generic_value_metadata(connected, shape):
    payload = dm(shape, recipient=OTHER, entry=OTHER)
    value_of(payload).update(id=PROFESSIONAL, account_id=PROFESSIONAL, metadata={"account_id": PROFESSIONAL, "destination_id": PROFESSIONAL})
    with pytest.raises(ValueError, match=ERROR):
        InboundPipelineService.process_raw_webhook_event(record(payload))
    assert not Conversation.objects.exists()


@pytest.mark.parametrize("conflict", ["alias", "envelope"])
def test_ambiguous_cross_workspace_identity_fails_without_writes(connected, conflict):
    other = make_organization(name="Other workspace")
    IntegrationConfig.objects.create(organization=other, provider="INSTAGRAM",
        metadata={"destination_id": OTHER, "account_id": PROFESSIONAL if conflict == "alias" else OTHER})
    payload = dm(recipient=OTHER if conflict == "envelope" else PROFESSIONAL)
    with pytest.raises(ValueError, match=ERROR):
        InboundPipelineService.process_raw_webhook_event(record(payload))
    assert not Message.objects.exists() and not Customer.objects.exists() and not Lead.objects.exists()


@pytest.mark.parametrize("inactive", ["config", "organization", "deleted_organization"])
def test_inactive_connection_or_workspace_is_not_resolved(connected, inactive):
    org, config, _ = connected
    obj = config if inactive == "config" else org
    setattr(obj, "is_deleted" if inactive == "deleted_organization" else "is_active", inactive == "deleted_organization")
    obj.save()
    with pytest.raises(ValueError, match=ERROR):
        InboundPipelineService.process_raw_webhook_event(record(dm()))


@pytest.mark.parametrize("shape", ["messaging", "changes"])
def test_echo_messages_never_enter_lead_pipeline(connected, shape):
    payload = dm(shape)
    value_of(payload)["message"]["is_echo"] = True
    assert InboundPipelineService.process_raw_webhook_event(record(payload))["messages_processed"] == 0
    assert not Message.objects.exists() and not Lead.objects.exists()


def test_safe_stage_diagnostics_and_celery_path(connected, caplog):
    secret_body = "need baby shoot PRIVATE-DM-NOT-FOR-LOGS"
    payload = dm(text=secret_body)
    caplog.set_level(logging.INFO)
    assert process_instagram_webhook_event_task.run(str(record(payload).pk))["leads_created"] == 1
    stages = [r for r in caplog.records if r.getMessage() == "instagram_destination_resolved"]
    assert len(stages) == 1
    assert stages[0].destination_id == PROFESSIONAL and stages[0].sender_id == CUSTOMER
    assert stages[0].resolution_matches == 1
    assert "PRIVATE-DM-NOT-FOR-LOGS" not in str([r.__dict__ for r in caplog.records])
    assert RawWebhookEvent.objects.get().status == "PROCESSED"


@pytest.mark.parametrize("shape", ["messaging", "changes"])
def test_signed_webhook_receiver_through_celery_and_lead_creation(connected, settings, shape):
    from apps.integrations.connection_service import app_credentials
    settings.META_APP_SECRET = "synthetic-webhook-secret"
    settings.META_INSTAGRAM_APP_SECRET = "synthetic-webhook-secret"
    payload = dm(shape)
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(app_credentials("INSTAGRAM")[1].encode(), body, hashlib.sha256).hexdigest()
    client = APIClient()
    for _ in range(2):
        response = client.post("/api/v1/webhooks/meta/instagram/", body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature)
        assert response.status_code == 200
    assert RawWebhookEvent.objects.count() == 1
    assert RawWebhookEvent.objects.get().status == "PROCESSED"
    assert Message.objects.count() == Lead.objects.count() == Conversation.objects.count() == 1


def test_whatsapp_retains_phone_number_routing_and_capture_all(connected):
    org, _, _ = connected
    phone_id = "109876543210987"
    IntegrationConfig.objects.create(organization=org, provider="WHATSAPP", metadata={"destination_id": phone_id})
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "109876543210999", "changes": [{"field": "messages", "value": {
        "metadata": {"phone_number_id": phone_id}, "messages": [{"id": "wamid.synthetic.regression", "from": "919876543210",
        "timestamp": str(int(timezone.now().timestamp())), "type": "text", "text": {"body": "Hello unrelated to any trigger"}}]}}]}]}
    event = InboundPipelineService.record_raw_event("WHATSAPP", json.dumps(payload).encode(), None, payload)[0]
    assert InboundPipelineService.process_raw_webhook_event(event)["leads_created"] == 1
    assert Message.objects.get().conversation.organization == org
    assert Message.objects.get().conversation.channel == "WHATSAPP"
