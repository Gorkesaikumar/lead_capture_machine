from tests.tenant_fixtures import route_payload, process_test_webhook_payload, configure_channel, test_workspace, make_organization, create_lead, add_member
"""
Comprehensive unit and integration tests for Meta WhatsApp Cloud API module.
Tests GET challenge verification, POST HMAC signature verification, status update tracking,
24-hour customer service window policy enforcement, template messaging, and Celery tasks.
"""
from datetime import datetime, timedelta, timezone as dt_timezone
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
from apps.customers.models import Customer, CustomerIdentity
from apps.integrations.meta.base import OutboundResult
from apps.integrations.meta.common.client import MetaGraphClient
from apps.integrations.meta.whatsapp.parser import WhatsAppInboundParser, WhatsAppStatusUpdate
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.integrations.meta.whatsapp.templates import WhatsAppTemplateBuilder
from apps.integrations.models import RawWebhookEvent
from apps.integrations.pipeline import InboundPipelineService
from apps.integrations.tasks import (
    process_whatsapp_webhook_event_task,
    send_whatsapp_booking_link_task,
    send_whatsapp_message_task,
)
from apps.leads.models import Lead, LeadTrigger
from apps.services.models import PhotographyService
from tests.fixtures.whatsapp_payloads import (
    SAMPLE_WA_BUTTON_REPLY_PAYLOAD,
    SAMPLE_WA_IMAGE_MESSAGE_PAYLOAD,
    SAMPLE_WA_STATUS_DELIVERED_PAYLOAD,
    SAMPLE_WA_STATUS_FAILED_PAYLOAD,
    SAMPLE_WA_STATUS_READ_PAYLOAD,
    SAMPLE_WA_STATUS_SENT_PAYLOAD,
    SAMPLE_WA_TEXT_MESSAGE_PAYLOAD,
)


@pytest.fixture
def test_app_secret():
    return "test_wa_meta_app_secret_12345"


@pytest.fixture
def test_verify_token():
    return "test_wa_verify_token_secret_67890"


@pytest.fixture
def configure_meta_settings(settings, test_app_secret, test_verify_token):
    settings.META_APP_SECRET = test_app_secret
    settings.META_VERIFY_TOKEN = test_verify_token
    settings.WHATSAPP_PHONE_NUMBER_ID = "109876543210"
    settings.WHATSAPP_ACCESS_TOKEN = "test_wa_cloud_access_token"
    settings.WHATSAPP_BOOKING_TEMPLATE_NAME = "studio_booking_invitation"
    settings.WHATSAPP_DEFAULT_LANGUAGE = "en"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    route_payload(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD)


def generate_meta_signature(raw_body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.django_db
class TestWhatsAppWebhookVerification:
    """Tests GET challenge verification for WhatsApp Cloud API webhooks."""

    def setup_method(self):
        self.client = APIClient()

    def test_get_challenge_success(self, configure_meta_settings, test_verify_token):
        url = reverse("api_v1:webhook-meta-whatsapp")
        response = self.client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": test_verify_token,
                "hub.challenge": "wa_challenge_code_12345",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode("utf-8") == "wa_challenge_code_12345"

    def test_get_challenge_invalid_verify_token_forbidden(self, configure_meta_settings):
        url = reverse("api_v1:webhook-meta-whatsapp")
        response = self.client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "invalid_token_999",
                "hub.challenge": "wa_challenge_code_12345",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestWhatsAppWebhookReceiver:
    """Tests POST webhook ingestion and raw event creation."""

    def setup_method(self):
        self.client = APIClient()

    def test_post_valid_signature_creates_raw_event_and_acks_quickly(
        self, configure_meta_settings, test_app_secret
    ):
        url = reverse("api_v1:webhook-meta-whatsapp")
        raw_body = json.dumps(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD).encode("utf-8")
        sig_header = generate_meta_signature(raw_body, test_app_secret)

        response = self.client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig_header,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["status"] == "received"
        assert "event_id" in response.data

        # Verify RawWebhookEvent was persisted
        event = RawWebhookEvent.objects.get(id=response.data["event_id"])
        assert event.channel == RawWebhookEvent.Channel.WHATSAPP
        assert event.status in [RawWebhookEvent.Status.PROCESSED, RawWebhookEvent.Status.PENDING]

    def test_post_invalid_signature_rejected_403(self, configure_meta_settings):
        url = reverse("api_v1:webhook-meta-whatsapp")
        raw_body = json.dumps(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD).encode("utf-8")

        response = self.client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid_hash_signature",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestWhatsAppPayloadParser:
    """Tests parsing WhatsApp messages and delivery status updates."""

    def test_parse_text_message(self):
        parser = WhatsAppInboundParser()
        assert parser.can_parse(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD) is True

        messages = parser.parse_messages(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "WHATSAPP"
        assert msg.external_user_id == "919876543210"
        assert msg.external_message_id == "wamid.HBgLMTIzNDU2Nzg5MA=="
        assert msg.sender_name == "Anita Roy"
        assert msg.sender_phone == "919876543210"
        assert msg.text == "Hi! Can you share pricing for a newborn shoot?"
        assert msg.message_type == "TEXT"

    def test_parse_image_message(self):
        parser = WhatsAppInboundParser()
        messages = parser.parse_messages(SAMPLE_WA_IMAGE_MESSAGE_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "WHATSAPP"
        assert msg.external_user_id == "919811122233"
        assert msg.sender_name == "Rahul Verma"
        assert msg.message_type == "IMAGE"
        assert msg.text == "Looking for this theme!"
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["media_id"] == "wa_media_id_555"

    def test_parse_interactive_button_reply(self):
        parser = WhatsAppInboundParser()
        messages = parser.parse_messages(SAMPLE_WA_BUTTON_REPLY_PAYLOAD)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.text == "Baby Photoshoot"
        assert msg.message_type == "TEXT"

    def test_parse_status_updates_delivered_and_failed(self):
        parser = WhatsAppInboundParser()

        # Delivered status
        del_statuses = parser.parse_status_updates(SAMPLE_WA_STATUS_DELIVERED_PAYLOAD)
        assert len(del_statuses) == 1
        st_del = del_statuses[0]
        assert st_del.external_message_id == "wamid.OUTBOUND_TEST_101"
        assert st_del.status == "delivered"
        assert st_del.recipient_id == "919876543210"
        assert st_del.error_details is None

        # Failed status
        failed_statuses = parser.parse_status_updates(SAMPLE_WA_STATUS_FAILED_PAYLOAD)
        assert len(failed_statuses) == 1
        st_fail = failed_statuses[0]
        assert st_fail.external_message_id == "wamid.OUTBOUND_TEST_FAILED_202"
        assert st_fail.status == "failed"
        assert st_fail.error_details["code"] == 131026
        assert "Recipient phone is out of service" in st_fail.error_details["message"]


@pytest.mark.django_db
class TestWhatsAppPipelineAndIdempotency:
    """Tests end-to-end processing and deduplication."""

    @pytest.fixture
    def newborn_trigger(self):
        svc = PhotographyService.objects.create(organization=test_workspace(),
            name="Newborn Session",
            slug="newborn-session",
            duration_minutes=90,
            base_price=500.00,
        )
        return LeadTrigger.objects.create(organization=test_workspace(),
            phrase="newborn shoot",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=svc,
            priority=10,
            is_active=True,
        )

    def test_pipeline_creates_customer_conversation_and_lead(
        self, configure_meta_settings, test_app_secret, newborn_trigger
    ):
        raw_body = json.dumps(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD).encode("utf-8")
        sig_header = generate_meta_signature(raw_body, test_app_secret)

        result = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=SAMPLE_WA_TEXT_MESSAGE_PAYLOAD,
            channel="WHATSAPP",
        )

        assert result["success"] is True
        assert result["messages_processed"] == 1
        assert result["new_messages_created"] == 1
        assert result["leads_created"] == 1

        # Customer & Identity checks
        customer = Customer.objects.get(identities__external_user_id="919876543210")
        assert customer.display_name == "Anita Roy"
        identity = customer.identities.get(channel="WHATSAPP")
        assert identity.external_user_id == "919876543210"

        # Conversation & Message checks
        conv = Conversation.objects.get(customer=customer, channel="WHATSAPP")
        assert conv.messages.count() == 1
        msg = conv.messages.first()
        assert msg.external_message_id == "wamid.HBgLMTIzNDU2Nzg5MA=="
        assert msg.text == "Hi! Can you share pricing for a newborn shoot?"

        # Lead checks
        lead = Lead.objects.get(customer=customer)
        assert lead.source_channel == "WHATSAPP"
        assert lead.service == newborn_trigger.service
        assert lead.status == Lead.Status.NEW

    def test_pipeline_idempotency_on_duplicate_webhook(
        self, configure_meta_settings, test_app_secret, newborn_trigger
    ):
        raw_body = json.dumps(SAMPLE_WA_TEXT_MESSAGE_PAYLOAD).encode("utf-8")
        sig_header = generate_meta_signature(raw_body, test_app_secret)

        # 1st delivery
        res1 = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=SAMPLE_WA_TEXT_MESSAGE_PAYLOAD,
            channel="WHATSAPP",
        )
        assert res1["new_messages_created"] == 1
        assert res1["leads_created"] == 1

        # 2nd delivery (duplicate)
        res2 = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=SAMPLE_WA_TEXT_MESSAGE_PAYLOAD,
            channel="WHATSAPP",
        )
        assert res2["is_duplicate"] is True
        assert res2["new_messages_created"] == 0
        assert res2["leads_created"] == 0

        # Assert no duplicates in DB
        assert Message.objects.filter(external_message_id="wamid.HBgLMTIzNDU2Nzg5MA==").count() == 1
        assert Lead.objects.filter(customer__identities__external_user_id="919876543210").count() == 1


@pytest.mark.django_db
class TestWhatsAppStatusUpdates:
    """Tests updating message delivery lifecycle statuses (SENT -> DELIVERED -> READ -> FAILED)."""

    def test_status_update_lifecycle_flow(self, configure_meta_settings, test_app_secret):
        # 1. Store initial outbound message
        customer = Customer.objects.create(organization=test_workspace(), display_name="Test Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="WHATSAPP",
            external_user_id="919876543210",
        )
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="WHATSAPP")
        msg = ConversationService.store_outbound_message(
            conversation=conv,
            text="Your appointment is confirmed!",
            external_message_id="wamid.OUTBOUND_TEST_101",
        )
        assert msg.delivery_status == Message.DeliveryStatus.SENT

        # 2. Ingest DELIVERED status webhook
        raw_body_del = json.dumps(SAMPLE_WA_STATUS_DELIVERED_PAYLOAD).encode("utf-8")
        sig_del = generate_meta_signature(raw_body_del, test_app_secret)
        process_test_webhook_payload(
            raw_body=raw_body_del,
            signature_header=sig_del,
            payload=SAMPLE_WA_STATUS_DELIVERED_PAYLOAD,
            channel="WHATSAPP",
        )
        msg.refresh_from_db()
        assert msg.delivery_status == Message.DeliveryStatus.DELIVERED

        # 3. Ingest READ status webhook
        raw_body_read = json.dumps(SAMPLE_WA_STATUS_READ_PAYLOAD).encode("utf-8")
        sig_read = generate_meta_signature(raw_body_read, test_app_secret)
        process_test_webhook_payload(
            raw_body=raw_body_read,
            signature_header=sig_read,
            payload=SAMPLE_WA_STATUS_READ_PAYLOAD,
            channel="WHATSAPP",
        )
        msg.refresh_from_db()
        assert msg.delivery_status == Message.DeliveryStatus.READ

    def test_failed_status_records_error_details(self, configure_meta_settings, test_app_secret):
        customer = Customer.objects.create(organization=test_workspace(), display_name="Failed Test Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="WHATSAPP",
            external_user_id="919876543210",
        )
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="WHATSAPP")
        msg = ConversationService.store_outbound_message(
            conversation=conv,
            text="Reminder message",
            external_message_id="wamid.OUTBOUND_TEST_FAILED_202",
        )

        raw_body = json.dumps(SAMPLE_WA_STATUS_FAILED_PAYLOAD).encode("utf-8")
        sig = generate_meta_signature(raw_body, test_app_secret)
        process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig,
            payload=SAMPLE_WA_STATUS_FAILED_PAYLOAD,
            channel="WHATSAPP",
        )

        msg.refresh_from_db()
        assert msg.delivery_status == Message.DeliveryStatus.FAILED
        assert msg.attachment_metadata["delivery_error"]["code"] == 131026


@pytest.mark.django_db
class TestWhatsAppCustomerServiceWindowAndTemplates:
    """Tests 24-hour service window rules and Meta template message dispatch."""

    def test_24h_window_active_sends_free_form_message(self, configure_meta_settings):
        # Create customer with recent inbound message (1 hour ago)
        customer = Customer.objects.create(organization=test_workspace(), display_name="Active Client")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="WHATSAPP",
            external_user_id="919888877776",
        )
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="WHATSAPP")
        ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_message_id": "wamid.RECENT_INBOUND_01",
            "external_user_id": "919888877776",
            "text": "Hello!",
            "message_type": "TEXT",
            "provider_timestamp": timezone.now() - timedelta(hours=1),
        }, organization=test_workspace())

        provider = WhatsAppMessagingProvider(organization=test_workspace())
        assert provider.is_free_form_permitted("919888877776") is True

        with patch.object(MetaGraphClient, "post") as mock_post:
            mock_post.return_value = {"messages": [{"id": "wamid.OUT_FF_1"}]}

            res = provider.send_booking_link_message(
                recipient_id="919888877776",
                booking_url="https://studio.com/book/token123",
                customer_name="Active Client",
                service_name="Maternity Shoot",
            )

            assert res.success is True
            mock_post.assert_called_once()
            call_payload = mock_post.call_args[0][1]
            assert call_payload["type"] == "text"
            assert "https://studio.com/book/token123" in call_payload["text"]["body"]

    def test_24h_window_expired_uses_approved_template(self, configure_meta_settings):
        # Customer has no recent message (older than 24 hours)
        customer = Customer.objects.create(organization=test_workspace(), display_name="Old Client")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="WHATSAPP",
            external_user_id="919111222333",
        )
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="WHATSAPP")
        ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_message_id": "wamid.OLD_INBOUND_01",
            "external_user_id": "919111222333",
            "text": "Old message",
            "message_type": "TEXT",
            "provider_timestamp": timezone.now() - timedelta(hours=30),
        }, organization=test_workspace())

        provider = WhatsAppMessagingProvider(organization=test_workspace())
        assert provider.is_free_form_permitted("919111222333") is False

        with patch.object(MetaGraphClient, "post") as mock_post:
            mock_post.return_value = {"messages": [{"id": "wamid.OUT_TPL_1"}]}

            res = provider.send_booking_link_message(
                recipient_id="919111222333",
                booking_url="https://studio.com/book/tokenXYZ",
                customer_name="Old Client",
                service_name="Baby Photoshoot",
            )

            assert res.success is True
            mock_post.assert_called_once()
            call_payload = mock_post.call_args[0][1]
            assert call_payload["type"] == "template"
            assert call_payload["template"]["name"] == "studio_booking_invitation"
            assert call_payload["template"]["language"]["code"] == "en"


@pytest.mark.django_db
class TestWhatsAppOutboundMessagingAndTasks:
    """Tests outbound provider methods and Celery tasks."""

    @patch.object(MetaGraphClient, "post")
    def test_send_media_message(self, mock_post, configure_meta_settings):
        mock_post.return_value = {"messages": [{"id": "wamid.MEDIA_OUT_1"}]}
        provider = WhatsAppMessagingProvider(organization=test_workspace())

        res = provider.send_media_message(
            recipient_id="919876543210",
            media_url="https://cdn.studio.com/preview.jpg",
            media_type="IMAGE",
            caption="Sample preview shot",
        )

        assert res.success is True
        assert res.external_message_id == "wamid.MEDIA_OUT_1"
        call_payload = mock_post.call_args[0][1]
        assert call_payload["type"] == "image"
        assert call_payload["image"]["link"] == "https://cdn.studio.com/preview.jpg"
        assert call_payload["image"]["caption"] == "Sample preview shot"

    def test_legacy_message_task_rejects_unscoped_send(self):
        with patch.object(WhatsAppMessagingProvider, "send_text_message") as send:
            result = send_whatsapp_message_task("919876543210", "Hello", "nonexistent-local-message")
        assert result["success"] is False
        send.assert_not_called()

    def test_legacy_booking_task_requires_conversation(self):
        with patch.object(WhatsAppMessagingProvider, "send_booking_link_message") as send:
            result = send_whatsapp_booking_link_task("919876543210", "https://studio.com/book/123", "Customer", "Portrait")
        assert result["success"] is False
        send.assert_not_called()
