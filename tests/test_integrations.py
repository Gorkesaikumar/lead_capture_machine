from tests.tenant_fixtures import route_payload, process_test_webhook_payload, configure_channel, test_workspace, make_organization, create_lead, add_member
"""
Comprehensive tests for Meta Integrations module (Instagram and WhatsApp).
Tests signature verification, payload parsing, pipeline orchestration, and outbound providers.
"""
from datetime import datetime, timezone as dt_timezone
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.urls import reverse
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.conversations.models import Conversation, Message
from apps.customers.models import Customer, CustomerIdentity
from apps.integrations.meta.base import (
    InboundMessageParser,
    NormalizedInboundMessage,
    OutboundResult,
)
from apps.integrations.meta.common.client import MetaGraphClient
from apps.integrations.meta.common.exceptions import (
    ProviderSendError,
    SignatureVerificationError,
    WebhookVerificationError,
)
from apps.integrations.meta.common.verifier import MetaSignatureVerifier
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.whatsapp.parser import WhatsAppInboundParser
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.integrations.pipeline import InboundPipelineService
from apps.leads.models import Lead, LeadTrigger
from apps.services.models import PhotographyService


@pytest.fixture
def test_app_secret():
    return "test_meta_app_secret_12345"


@pytest.fixture
def test_verify_token():
    return "test_verify_token_secret_67890"


@pytest.fixture
def configure_meta_settings(settings, test_app_secret, test_verify_token):
    settings.META_APP_SECRET = test_app_secret
    settings.META_VERIFY_TOKEN = test_verify_token
    settings.INSTAGRAM_PAGE_ACCESS_TOKEN = "test_ig_access_token"
    settings.WHATSAPP_ACCESS_TOKEN = "test_wa_access_token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "109876543210"


def generate_meta_signature(raw_body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.django_db
class TestMetaSignatureVerifier:
    """Tests cryptographic signature validation and GET challenge verification."""

    def test_verify_valid_signature(self, test_app_secret):
        body = b'{"object": "instagram", "entry": []}'
        sig_header = generate_meta_signature(body, test_app_secret)
        assert MetaSignatureVerifier.verify_signature(body, sig_header, app_secret=test_app_secret) is True

    def test_verify_invalid_signature_raises_error(self, test_app_secret):
        body = b'{"object": "instagram"}'
        invalid_header = "sha256=invalidhash0000000000000000000000000000000000000000000000000000"
        with pytest.raises(SignatureVerificationError, match="Signature validation failed"):
            MetaSignatureVerifier.verify_signature(body, invalid_header, app_secret=test_app_secret)

    def test_missing_signature_header_raises_error(self, test_app_secret):
        body = b'{"object": "instagram"}'
        with pytest.raises(SignatureVerificationError, match="Missing signature header"):
            MetaSignatureVerifier.verify_signature(body, None, app_secret=test_app_secret)

    def test_verify_challenge_success(self, test_verify_token):
        challenge = MetaSignatureVerifier.verify_challenge(
            mode="subscribe",
            verify_token=test_verify_token,
            challenge="test_challenge_code_999",
            expected_token=test_verify_token,
        )
        assert challenge == "test_challenge_code_999"

    def test_verify_challenge_wrong_token_raises_error(self, test_verify_token):
        with pytest.raises(WebhookVerificationError, match="Verification token mismatch"):
            MetaSignatureVerifier.verify_challenge(
                mode="subscribe",
                verify_token="wrong_token",
                challenge="12345",
                expected_token=test_verify_token,
            )

    def test_verify_challenge_wrong_mode_raises_error(self, test_verify_token):
        with pytest.raises(WebhookVerificationError, match="Invalid hub.mode"):
            MetaSignatureVerifier.verify_challenge(
                mode="unsubscribe",
                verify_token=test_verify_token,
                challenge="12345",
                expected_token=test_verify_token,
            )


class TestInstagramInboundParser:
    """Tests parsing raw Instagram webhook payloads into NormalizedInboundMessage."""

    def test_parse_text_message(self):
        parser = InstagramInboundParser()
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400000000000",
                    "time": 1723057200000,
                    "messaging": [
                        {
                            "sender": {"id": "ig_user_456"},
                            "recipient": {"id": "17841400000000000"},
                            "timestamp": 1723057200000,
                            "message": {
                                "mid": "m_ig_mid_12345",
                                "text": "Hello, how much for a maternity photoshoot?",
                            },
                        }
                    ],
                }
            ],
        }

        assert parser.can_parse(payload) is True
        messages = parser.parse_messages(payload)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "INSTAGRAM"
        assert msg.external_user_id == "ig_user_456"
        assert msg.external_message_id == "m_ig_mid_12345"
        assert msg.text == "Hello, how much for a maternity photoshoot?"
        assert msg.message_type == "TEXT"
        assert msg.attachments == []
        assert isinstance(msg.provider_timestamp, datetime)

    def test_parse_media_attachments(self):
        parser = InstagramInboundParser()
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400000000000",
                    "messaging": [
                        {
                            "sender": {"id": "ig_user_789"},
                            "message": {
                                "mid": "m_ig_media_999",
                                "attachments": [
                                    {
                                        "type": "image",
                                        "payload": {"url": "https://cdn.instagram.com/sample.jpg"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        messages = parser.parse_messages(payload)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == "IMAGE"
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["url"] == "https://cdn.instagram.com/sample.jpg"

    def test_ignore_echo_messages(self):
        parser = InstagramInboundParser()
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "90001",
                    "messaging": [
                        {
                            "sender": {"id": "my_studio_page"},
                            "message": {
                                "mid": "m_echo_001",
                                "is_echo": True,
                                "text": "We received your inquiry!",
                            },
                        }
                    ]
                }
            ],
        }
        messages = parser.parse_messages(payload)
        assert len(messages) == 0


class TestWhatsAppInboundParser:
    """Tests parsing raw WhatsApp Cloud API webhook payloads into NormalizedInboundMessage."""

    def test_parse_text_message(self):
        parser = WhatsAppInboundParser()
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA_ID_001",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15550001111",
                                    "phone_number_id": "100001",
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Priya Sharma"},
                                        "wa_id": "919876543210",
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid.ABGG1234567890",
                                        "timestamp": "1723057200",
                                        "type": "text",
                                        "text": {"body": "I would like to book a family portrait session."},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        assert parser.can_parse(payload) is True
        messages = parser.parse_messages(payload)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.channel == "WHATSAPP"
        assert msg.external_user_id == "919876543210"
        assert msg.external_message_id == "wamid.ABGG1234567890"
        assert msg.sender_name == "Priya Sharma"
        assert msg.sender_phone == "919876543210"
        assert msg.text == "I would like to book a family portrait session."
        assert msg.message_type == "TEXT"
        assert isinstance(msg.provider_timestamp, datetime)

    def test_parse_image_message(self):
        parser = WhatsAppInboundParser()
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [{"profile": {"name": "Alex"}, "wa_id": "12345"}],
                                "messages": [
                                    {
                                        "from": "12345",
                                        "id": "wamid.MEDIA_001",
                                        "type": "image",
                                        "image": {
                                            "id": "media_id_777",
                                            "mime_type": "image/jpeg",
                                            "caption": "Can we do this style?",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            ],
        }
        messages = parser.parse_messages(payload)
        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == "IMAGE"
        assert msg.text == "Can we do this style?"
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["media_id"] == "media_id_777"


@pytest.mark.django_db
class TestInboundPipelineOrchestration:
    """
    Tests full pipeline orchestration:
    Webhook Payload -> Normalized Message -> Customer Resolution -> Conversation Storage -> Lead Detection.
    """

    @pytest.fixture
    def baby_shoot_trigger(self):
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Newborn Baby Shoot",
            slug="newborn-baby-shoot",
            duration_minutes=60,
            base_price=350.00,
        )
        return LeadTrigger.objects.create(organization=test_workspace(),
            phrase="baby shoot",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=service,
            priority=10,
            is_active=True,
        )

    def test_pipeline_end_to_end_instagram_lead_creation(
        self, configure_meta_settings, test_app_secret, baby_shoot_trigger
    ):
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400000000000",
                    "messaging": [
                        {
                            "sender": {"id": "ig_cust_101"},
                            "timestamp": 1723057200000,
                            "message": {
                                "mid": "mid_ig_unique_001",
                                "text": "Hi! What are the rates for a baby shoot session?",
                            },
                        }
                    ],
                }
            ],
        }
        route_payload(payload)
        raw_body = json.dumps(payload).encode("utf-8")
        sig_header = generate_meta_signature(raw_body, test_app_secret)

        result = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=payload,
            verify_signature=True,
        )

        assert result["success"] is True
        assert result["messages_processed"] == 1
        assert result["new_messages_created"] == 1
        assert result["leads_created"] == 1

        # Verify Customer & Identity was created
        customer = Customer.objects.get(identities__external_user_id="ig_cust_101")
        assert customer is not None
        identity = customer.identities.get(channel="INSTAGRAM")
        assert identity.external_user_id == "ig_cust_101"

        # Verify Conversation & Message was stored
        conv = Conversation.objects.get(customer=customer, channel="INSTAGRAM")
        assert conv.messages.count() == 1
        msg = conv.messages.first()
        assert msg.external_message_id == "mid_ig_unique_001"
        assert msg.text == "Hi! What are the rates for a baby shoot session?"

        # Verify Lead was automatically created and mapped to trigger's service
        lead = Lead.objects.get(customer=customer)
        assert lead.source_channel == "INSTAGRAM"
        assert lead.service == baby_shoot_trigger.service
        assert lead.status == Lead.Status.NEW

    def test_pipeline_idempotency_duplicate_webhook(
        self, configure_meta_settings, test_app_secret, baby_shoot_trigger
    ):
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "90001",
                    "messaging": [
                        {
                            "sender": {"id": "ig_cust_idempotent"},
                            "message": {
                                "mid": "mid_duplicate_test",
                                "text": "Inquiry about baby shoot pricing",
                            },
                        }
                    ]
                }
            ],
        }
        route_payload(payload)
        raw_body = json.dumps(payload).encode("utf-8")
        sig_header = generate_meta_signature(raw_body, test_app_secret)

        # First delivery
        res1 = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=payload,
        )
        assert res1["new_messages_created"] == 1
        assert res1["leads_created"] == 1

        # Second delivery of same webhook (idempotency test)
        res2 = process_test_webhook_payload(
            raw_body=raw_body,
            signature_header=sig_header,
            payload=payload,
        )
        assert res2["new_messages_created"] == 0
        assert res2["leads_created"] == 0

        # Only one message and one lead should exist
        assert Message.objects.filter(external_message_id="mid_duplicate_test").count() == 1
        assert Lead.objects.filter(customer__identities__external_user_id="ig_cust_idempotent").count() == 1


@pytest.mark.django_db
class TestMetaWebhookEndpoints:
    """Tests HTTP endpoints for Meta GET verification and POST payload ingestion."""

    def setup_method(self):
        self.client = APIClient()

    def test_get_webhook_challenge_success(self, configure_meta_settings, test_verify_token):
        url = reverse("api_v1:integrations:meta-whatsapp-webhook")
        response = self.client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": test_verify_token,
                "hub.challenge": "challenge_string_abc123",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode("utf-8") == "challenge_string_abc123"

    def test_get_webhook_challenge_forbidden_wrong_token(self, configure_meta_settings):
        url = reverse("api_v1:integrations:meta-instagram-webhook")
        response = self.client.get(
            url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge_123",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_webhook_valid_signature_success(
        self, configure_meta_settings, test_app_secret
    ):
        url = reverse("api_v1:integrations:meta-whatsapp-webhook")
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "90001"},
                                "contacts": [{"profile": {"name": "Test User"}, "wa_id": "99999"}],
                                "messages": [
                                    {
                                        "from": "99999",
                                        "id": "wamid.HTTP_TEST_1",
                                        "type": "text",
                                        "text": {"body": "Hello studio!"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ],
        }
        route_payload(payload)
        raw_body = json.dumps(payload).encode("utf-8")
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
        assert Message.objects.filter(external_message_id="wamid.HTTP_TEST_1").count() == 1

    def test_post_webhook_invalid_signature_forbidden(
        self, configure_meta_settings
    ):
        url = reverse("api_v1:integrations:meta-instagram-webhook")
        raw_body = b'{"object": "instagram"}'

        response = self.client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid_hash_signature",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOutboundMessagingProviders:
    """Tests outbound messaging providers for Instagram and WhatsApp."""

    @patch.object(MetaGraphClient, "post")
    def test_instagram_provider_send_text(self, mock_post):
        mock_post.return_value = {"message_id": "mid_ig_out_101"}
        provider = InstagramMessagingProvider(access_token="fake_token")

        res = provider.send_text_message(recipient_id="ig_user_123", text="Your booking is confirmed!")
        assert res.success is True
        assert res.external_message_id == "mid_ig_out_101"
        mock_post.assert_called_once_with(
            "me/messages",
            {"recipient": {"id": "ig_user_123"}, "message": {"text": "Your booking is confirmed!"}},
            access_token="fake_token",
        )

    @patch.object(MetaGraphClient, "post")
    def test_whatsapp_provider_send_text(self, mock_post):
        mock_post.return_value = {"messages": [{"id": "wamid.WA_OUT_202"}]}
        provider = WhatsAppMessagingProvider(phone_number_id="10001", access_token="fake_wa_token")

        res = provider.send_text_message(recipient_id="919876543210", text="Here is your booking link: https://studio.com/book/xyz")
        assert res.success is True
        assert res.external_message_id == "wamid.WA_OUT_202"
        mock_post.assert_called_once()

    def test_outbound_dispatch_api_view_authenticated_admin_allowed(self, configure_meta_settings):
        client = APIClient()
        admin_user = User.objects.create_superuser(
            email="admin_integrations@studio.com",
            password="AdminPassword123!",
            full_name="Admin Integrations",
        )
        add_member(admin_user)
        client.force_authenticate(user=admin_user)

        from apps.customers.models import Customer, CustomerIdentity
        customer = Customer.objects.create(organization=test_workspace(), display_name="API Recipient")
        CustomerIdentity.objects.create(
            customer=customer, channel="WHATSAPP", external_user_id="919876543210"
        )

        from apps.conversations.models import Conversation, Message
        from django.utils import timezone
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="WHATSAPP")
        Message.objects.create(conversation=conv, direction="INBOUND", provider_timestamp=timezone.now(), text="Hi")
        configure_channel(channel="WHATSAPP")
        with patch.object(WhatsAppMessagingProvider, "send_text_message") as mock_send:
            mock_send.return_value = OutboundResult(
                success=True, external_message_id="wamid.API_TEST_100"
            )

            url = reverse("api_v1:integrations:outbound-send")
            response = client.post(
                url,
                {
                    "channel": "WHATSAPP",
                    "recipient_id": "919876543210",
                    "text": "Hello from admin dashboard!",
                },
                format="json",
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            assert response.data["delivery_status"] == "QUEUED"
            assert response.data["external_message_id"] == ""

    def test_outbound_dispatch_api_view_unauthenticated_rejected(self, configure_meta_settings):
        client = APIClient()
        url = reverse("api_v1:integrations:outbound-send")
        response = client.post(
            url,
            {
                "channel": "WHATSAPP",
                "recipient_id": "919876543210",
                "text": "Hello from anonymous!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_outbound_dispatch_api_view_inactive_admin_rejected(self, configure_meta_settings):
        client = APIClient()
        admin_user = User.objects.create_superuser(
            email="inactive_admin@studio.com",
            password="AdminPassword123!",
            full_name="Inactive Admin",
        )
        admin_user.is_active = False
        admin_user.save()
        
        add_member(admin_user)
        client.force_authenticate(user=admin_user)

        url = reverse("api_v1:integrations:outbound-send")
        response = client.post(
            url,
            {
                "channel": "WHATSAPP",
                "recipient_id": "919876543210",
                "text": "Hello from inactive admin!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
