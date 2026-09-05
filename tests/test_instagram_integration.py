from tests.tenant_fixtures import route_payload, process_test_webhook_payload, configure_channel, test_workspace, make_organization, create_lead, add_member
"""
Comprehensive tests for Instagram Messaging Integration inside integrations.meta.instagram.
Tests GET webhook verification, POST receiver, signature validation, parser, idempotency,
async Celery processing, outbound text/booking-link messaging, retries, and token security.
"""
import hashlib
import hmac
import json
import logging
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.urls import reverse
import pytest
import requests
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.conversations.models import Conversation, Message
from apps.customers.models import Customer, CustomerIdentity
from apps.integrations.meta.common.client import MetaGraphClient, mask_token
from apps.integrations.meta.common.exceptions import (
    ProviderSendError,
    SignatureVerificationError,
    WebhookVerificationError,
)
from apps.integrations.meta.common.verifier import MetaSignatureVerifier
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.models import RawWebhookEvent
from apps.integrations.pipeline import InboundPipelineService
from apps.integrations.tasks import process_instagram_webhook_event_task
from apps.leads.models import Lead, LeadTrigger
from apps.services.models import PhotographyService
from tests.fixtures.instagram_payloads import (
    INSTAGRAM_ECHO_MESSAGE_PAYLOAD,
    INSTAGRAM_IMAGE_ATTACHMENT_PAYLOAD,
    INSTAGRAM_MULTIPLE_MESSAGES_PAYLOAD,
    INSTAGRAM_QUICK_REPLY_PAYLOAD,
    INSTAGRAM_READ_RECEIPT_PAYLOAD,
    INSTAGRAM_STORY_MENTION_PAYLOAD,
    INSTAGRAM_TEXT_MESSAGE_PAYLOAD,
)


@pytest.fixture
def test_app_secret():
    return "meta_app_secret_test_998877"


@pytest.fixture
def test_verify_token():
    return "meta_verify_token_test_112233"


@pytest.fixture
def configure_instagram_settings(settings, test_app_secret, test_verify_token):
    settings.META_APP_SECRET = test_app_secret
    settings.META_VERIFY_TOKEN = test_verify_token
    settings.INSTAGRAM_PAGE_ACCESS_TOKEN = "EAAGtest_instagram_page_token_abcdef"
    settings.META_GRAPH_API_VERSION = "v21.0"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    route_payload(INSTAGRAM_TEXT_MESSAGE_PAYLOAD)


def make_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ==============================================================================
# 1. Webhook GET Verification Challenge Tests
# ==============================================================================

@pytest.mark.django_db
class TestInstagramWebhookVerification:
    """Tests GET challenge verification on /api/v1/webhooks/meta/instagram/"""

    def test_get_challenge_success(self, client, configure_instagram_settings, test_verify_token):
        url = "/api/v1/webhooks/meta/instagram/"
        response = client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": test_verify_token,
                "hub.challenge": "instagram_challenge_token_xyz",
            },
        )
        assert response.status_code == 200
        assert response.content.decode("utf-8") == "instagram_challenge_token_xyz"
        assert response["Content-Type"].startswith("text/plain")

    def test_get_challenge_invalid_verify_token_forbidden(self, client, configure_instagram_settings):
        url = "/api/v1/webhooks/meta/instagram/"
        response = client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token_value",
                "hub.challenge": "challenge_xyz",
            },
        )
        assert response.status_code == 403
        assert response.content.decode("utf-8") == "Forbidden"

    def test_get_challenge_invalid_mode_forbidden(self, client, configure_instagram_settings, test_verify_token):
        url = "/api/v1/webhooks/meta/instagram/"
        response = client.get(
            url,
            {
                "hub.mode": "other_mode",
                "hub.verify_token": test_verify_token,
                "hub.challenge": "challenge_xyz",
            },
        )
        assert response.status_code == 403


# ==============================================================================
# 2. Webhook POST Receiver & Signature Validation Tests
# ==============================================================================

@pytest.mark.django_db
class TestInstagramWebhookReceiver:
    """Tests POST receiver, HMAC validation, and quick 200 OK acknowledgment."""

    def test_post_valid_signature_creates_raw_event_and_acks_quickly(
        self, client, configure_instagram_settings, test_app_secret
    ):
        url = "/api/v1/webhooks/meta/instagram/"
        raw_body = json.dumps(INSTAGRAM_TEXT_MESSAGE_PAYLOAD).encode("utf-8")
        sig_header = make_signature(raw_body, test_app_secret)

        response = client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig_header,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "received"
        event_id = response.json()["event_id"]

        # Verify RawWebhookEvent was recorded
        raw_event = RawWebhookEvent.objects.get(id=event_id)
        assert raw_event.channel == RawWebhookEvent.Channel.INSTAGRAM
        assert raw_event.status in [RawWebhookEvent.Status.PENDING, RawWebhookEvent.Status.PROCESSED]
        assert raw_event.signature == sig_header

    def test_post_invalid_signature_rejected_403(
        self, client, configure_instagram_settings
    ):
        url = "/api/v1/webhooks/meta/instagram/"
        raw_body = json.dumps(INSTAGRAM_TEXT_MESSAGE_PAYLOAD).encode("utf-8")

        response = client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=badsignature000000000000000000000000000000000000000000000000000",
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Signature verification failed."
        assert RawWebhookEvent.objects.count() == 0

    def test_post_missing_signature_header_rejected_403(
        self, client, configure_instagram_settings
    ):
        url = "/api/v1/webhooks/meta/instagram/"
        raw_body = json.dumps(INSTAGRAM_TEXT_MESSAGE_PAYLOAD).encode("utf-8")

        response = client.post(
            url,
            data=raw_body,
            content_type="application/json",
        )

        assert response.status_code == 403
        assert RawWebhookEvent.objects.count() == 0


# ==============================================================================
# 3. Payload Parser Tests with Sanitized Meta Payloads
# ==============================================================================

class TestInstagramPayloadParser:
    """Tests InstagramInboundParser across various message and event types."""

    def setup_method(self):
        self.parser = InstagramInboundParser()

    def test_parse_text_message_payload(self):
        assert self.parser.can_parse(INSTAGRAM_TEXT_MESSAGE_PAYLOAD) is True
        messages = self.parser.parse_messages(INSTAGRAM_TEXT_MESSAGE_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "INSTAGRAM"
        assert msg.external_user_id == "ig_user_112233"
        assert msg.external_message_id == "aWdfbWlkX3RleHRfMTIzNDU"
        assert msg.text == "Hi! Do you offer outdoor portrait shoots?"
        assert msg.message_type == "TEXT"
        assert msg.attachments == []

    def test_parse_image_attachment_payload(self):
        messages = self.parser.parse_messages(INSTAGRAM_IMAGE_ATTACHMENT_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "INSTAGRAM"
        assert msg.external_user_id == "ig_user_445566"
        assert msg.message_type == "IMAGE"
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["url"] == "https://lookaside.fbsbx.com/ig_messaging_cdn/sample_moodboard.jpg"

    def test_parse_story_mention_payload(self):
        messages = self.parser.parse_messages(INSTAGRAM_STORY_MENTION_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "INSTAGRAM"
        assert msg.external_user_id == "ig_user_778899"
        assert msg.message_type == "IMAGE"
        assert "[Instagram Story Mention]" in msg.text

    def test_parse_quick_reply_payload(self):
        messages = self.parser.parse_messages(INSTAGRAM_QUICK_REPLY_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.text == "Wedding Photography"

    def test_parse_echo_message_ignored(self):
        messages = self.parser.parse_messages(INSTAGRAM_ECHO_MESSAGE_PAYLOAD)
        assert len(messages) == 0

    def test_parse_read_receipt_ignored(self):
        messages = self.parser.parse_messages(INSTAGRAM_READ_RECEIPT_PAYLOAD)
        assert len(messages) == 0

    def test_parse_multiple_messages_in_single_entry(self):
        messages = self.parser.parse_messages(INSTAGRAM_MULTIPLE_MESSAGES_PAYLOAD)
        assert len(messages) == 2
        assert messages[0].external_user_id == "ig_user_multi_1"
        assert messages[1].external_user_id == "ig_user_multi_2"


# ==============================================================================
# 4. Asynchronous Pipeline & Idempotency Tests
# ==============================================================================

@pytest.mark.django_db
class TestInstagramPipelineAndIdempotency:
    """Tests end-to-end webhook processing, Celery task, and idempotency guarantees."""

    @pytest.fixture
    def outdoor_shoot_trigger(self):
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Outdoor Portrait Shoot",
            slug="outdoor-portrait-shoot",
            duration_minutes=90,
            base_price=450.00,
        )
        return LeadTrigger.objects.create(organization=test_workspace(),
            phrase="outdoor portrait",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=service,
            priority=10,
            is_active=True,
        )

    def test_full_pipeline_processing_creates_customer_conversation_and_lead(
        self, outdoor_shoot_trigger
    ):
        raw_event, _ = InboundPipelineService.record_raw_event(
            channel="INSTAGRAM",
            raw_body=json.dumps(INSTAGRAM_TEXT_MESSAGE_PAYLOAD).encode("utf-8"),
            signature_header="sha256=test",
            payload=INSTAGRAM_TEXT_MESSAGE_PAYLOAD,
        )

        route_payload(raw_event.payload)
        result = process_instagram_webhook_event_task(str(raw_event.id))
        assert result["messages_processed"] == 1
        assert result["new_messages_created"] == 1
        assert result["leads_created"] == 1

        # Check raw event state
        raw_event.refresh_from_db()
        assert raw_event.status == RawWebhookEvent.Status.PROCESSED
        assert raw_event.messages_count == 1
        assert raw_event.processed_at is not None

        # Check Customer & Identity
        customer = Customer.objects.get(identities__external_user_id="ig_user_112233")
        assert customer.identities.filter(channel="INSTAGRAM").exists()

        # Check Conversation & Message
        conv = Conversation.objects.get(customer=customer, channel="INSTAGRAM")
        assert conv.messages.count() == 1
        msg = conv.messages.first()
        assert msg.external_message_id == "aWdfbWlkX3RleHRfMTIzNDU"
        assert msg.text == "Hi! Do you offer outdoor portrait shoots?"

        # Check Lead Detection
        lead = Lead.objects.get(customer=customer)
        assert lead.source_channel == "INSTAGRAM"
        assert lead.service == outdoor_shoot_trigger.service
        assert lead.status == Lead.Status.NEW

    def test_strict_idempotency_duplicate_webhook_does_not_duplicate_lead_or_message(
        self, client, configure_instagram_settings, test_app_secret, outdoor_shoot_trigger
    ):
        url = "/api/v1/webhooks/meta/instagram/"
        raw_body = json.dumps(INSTAGRAM_TEXT_MESSAGE_PAYLOAD).encode("utf-8")
        sig_header = make_signature(raw_body, test_app_secret)

        # 1. First webhook delivery
        resp1 = client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig_header,
        )
        assert resp1.status_code == 200
        event_id = resp1.json()["event_id"]

        # Run task to complete first event
        process_instagram_webhook_event_task(event_id)

        assert Message.objects.filter(external_message_id="aWdfbWlkX3RleHRfMTIzNDU").count() == 1
        assert Lead.objects.filter(customer__identities__external_user_id="ig_user_112233").count() == 1

        # 2. Second delivery of exact same webhook payload (Meta retry)
        resp2 = client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig_header,
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate_ignored"

        # Assert no duplicates were created
        assert Message.objects.filter(external_message_id="aWdfbWlkX3RleHRfMTIzNDU").count() == 1
        assert Lead.objects.filter(customer__identities__external_user_id="ig_user_112233").count() == 1
        assert RawWebhookEvent.objects.count() == 1


# ==============================================================================
# 5. Outbound Messaging & Booking Link Delivery Tests
# ==============================================================================

@pytest.mark.django_db
class TestInstagramOutboundMessaging:
    """Tests outbound text messaging, booking links, and media delivery."""

    @patch.object(MetaGraphClient, "post")
    def test_send_text_message_success(self, mock_post):
        mock_post.return_value = {"message_id": "mid_ig_sent_001"}
        provider = InstagramMessagingProvider(access_token="test_token")

        res = provider.send_text_message(
            recipient_id="ig_user_123",
            text="Thank you for inquiring! We have dates available this Saturday.",
        )

        assert res.success is True
        assert res.external_message_id == "mid_ig_sent_001"
        mock_post.assert_called_once_with(
            "me/messages",
            {
                "recipient": {"id": "ig_user_123"},
                "message": {"text": "Thank you for inquiring! We have dates available this Saturday."},
            },
            access_token="test_token",
        )

    @patch.object(MetaGraphClient, "post")
    def test_send_booking_link_message_template_success(self, mock_post):
        mock_post.return_value = {"message_id": "mid_ig_booking_link_101"}
        provider = InstagramMessagingProvider(access_token="test_token")

        booking_url = "https://studio.com/book/secure-token-9988"
        res = provider.send_booking_link_message(
            recipient_id="ig_user_456",
            booking_url=booking_url,
            title="Book Your Outdoor Shoot",
            subtitle="Choose your preferred session time.",
        )

        assert res.success is True
        assert res.external_message_id == "mid_ig_booking_link_101"
        call_args = mock_post.call_args[0]
        assert call_args[0] == "me/messages"
        payload = call_args[1]
        assert payload["recipient"]["id"] == "ig_user_456"
        elements = payload["message"]["attachment"]["payload"]["elements"]
        assert elements[0]["title"] == "Book Your Outdoor Shoot"
        assert elements[0]["buttons"][0]["url"] == booking_url

    @patch.object(MetaGraphClient, "post")
    def test_send_booking_link_fallback_to_plain_text_on_template_error(self, mock_post):
        # Template call fails with 400 (e.g. account not eligible for rich templates)
        # Second call (plain text fallback) succeeds
        mock_post.side_effect = [
            ProviderSendError("Meta API error: Template not supported"),
            {"message_id": "mid_ig_fallback_plain"},
        ]
        provider = InstagramMessagingProvider(access_token="test_token")

        res = provider.send_booking_link_message(
            recipient_id="ig_user_789",
            booking_url="https://studio.com/book/token-xyz",
            title="Book Session",
        )

        assert res.success is True
        assert res.external_message_id == "mid_ig_fallback_plain"
        assert mock_post.call_count == 2


# ==============================================================================
# 6. HTTP Client Resilience, Retries, & Security Tests
# ==============================================================================

class TestMetaClientResilienceAndSecurity:
    """Tests HTTP timeouts, retries, and token security."""

    def test_client_uses_configurable_api_version(self, settings):
        settings.META_GRAPH_API_VERSION = "v22.0"
        client = MetaGraphClient(access_token="test_token")
        assert client.api_version == "v22.0"
        assert client.base_url == "https://graph.facebook.com/v22.0"

    def test_mask_token_prevents_token_leakage(self):
        token = "EAAG1234567890abcdefghijklmnopqrstuvwxyz"
        masked = mask_token(token)
        assert token not in masked
        assert masked == "[REDACTED]"
        assert mask_token("") == "[MISSING]"
        assert mask_token("short") == "[REDACTED]"

    @patch.object(requests.Session, "post")
    def test_client_handles_timeout(self, mock_session_post):
        mock_session_post.side_effect = requests.exceptions.Timeout("Connection timed out after 10s")
        client = MetaGraphClient(access_token="test_token", timeout=5)

        with pytest.raises(ProviderSendError, match="Request timeout"):
            client.post("me/messages", {"text": "hello"})

    @patch.object(requests.Session, "post")
    def test_client_raises_clean_error_on_meta_error_response(self, mock_session_post):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Invalid OAuth access token", "code": 190}}'
        mock_response.json.return_value = {
            "error": {"message": "Invalid OAuth access token", "code": 190}
        }
        mock_session_post.return_value = mock_response

        client = MetaGraphClient(access_token="secret_token_never_expose")

        with pytest.raises(ProviderSendError) as exc_info:
            client.post("me/messages", {"text": "test"})

        error_str = str(exc_info.value)
        assert "Meta API error (190)" in error_str
        assert exc_info.value.code == 190
        # Ensure secret token is NOT in exception message
        assert "secret_token_never_expose" not in error_str
