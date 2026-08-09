"""
Tests for Instagram Outbound Messaging.
Validates recipient ID resolution, payload formatting, error handling, and 24h window enforcement.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from django.contrib.auth import get_user_model
User = get_user_model()
from apps.customers.models import Customer, CustomerIdentity
from apps.conversations.models import Conversation, Message
from apps.leads.models import Lead
from apps.services.models import PhotographyService
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.common.exceptions import ProviderSendError


class InstagramOutboundMessagingTests(TestCase):
    """
    Comprehensive tests for Instagram Direct outbound messaging.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@v4studio.test",
            password="StrongPassword123!",
            full_name="Admin User",
        )
        self.client.force_authenticate(user=self.admin)

        self.service = PhotographyService.objects.create(
            name="Baby Portrait Session",
            slug="baby-portrait-session",
            base_price=15000.00,
            duration_minutes=60,
            is_active=True,
        )

        self.customer = Customer.objects.create(
            display_name="Gorke Saikumar",
            primary_phone="+919876543210",
        )

        self.valid_igsid = "1784145522334455"
        self.identity = CustomerIdentity.objects.create(
            customer=self.customer,
            channel="INSTAGRAM",
            external_user_id=self.valid_igsid,
            username="gorkesakumar",
        )

        self.conversation = Conversation.objects.create(
            customer=self.customer,
            channel="INSTAGRAM",
        )

        # Seed an inbound message within 24h window
        self.inbound_msg = Message.objects.create(
            conversation=self.conversation,
            direction=Message.Direction.INBOUND,
            text="Hi, I want to book a session",
            external_message_id="mid_test_123",
            created_at=timezone.now(),
        )

        self.lead = Lead.objects.create(
            customer=self.customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=self.conversation,
        )

    def test_provider_validates_recipient_id(self):
        """Provider must reject invalid/dummy/UUID recipient IDs."""
        # Empty
        valid, err = InstagramMessagingProvider.validate_recipient_id("")
        self.assertFalse(valid)

        # Mock dummy
        valid, err = InstagramMessagingProvider.validate_recipient_id("USER_A")
        self.assertFalse(valid)
        self.assertIn("Invalid Instagram recipient ID", err)

        # Internal UUID
        valid, err = InstagramMessagingProvider.validate_recipient_id("0ebe336d-e5fb-46de-bfdc-c171b1505a31")
        self.assertFalse(valid)
        self.assertIn("internal database UUID", err)

        # Email
        valid, err = InstagramMessagingProvider.validate_recipient_id("user@test.com")
        self.assertFalse(valid)

        # Phone with plus
        valid, err = InstagramMessagingProvider.validate_recipient_id("+919876543210")
        self.assertFalse(valid)

        # Valid numeric IGSID
        valid, err = InstagramMessagingProvider.validate_recipient_id("1784145522334455")
        self.assertTrue(valid)
        self.assertIsNone(err)

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_send_message_uses_igsid_not_uuid_or_phone(self, mock_post):
        """Outbound message MUST use the CustomerIdentity.external_user_id (IGSID), never UUID or phone."""
        mock_post.return_value = {"message_id": "mid_outbound_999"}

        url = f"/api/v1/leads/{self.lead.id}/messages/"
        payload = {"message": "Hello from studio!"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_post.assert_called_once()
        endpoint, data = mock_post.call_args[0]
        self.assertEqual(endpoint, "me/messages")
        self.assertEqual(data["recipient"]["id"], self.valid_igsid)
        self.assertNotEqual(data["recipient"]["id"], str(self.customer.id))
        self.assertNotEqual(data["recipient"]["id"], str(self.lead.id))
        self.assertNotEqual(data["recipient"]["id"], self.customer.primary_phone)
        self.assertNotEqual(data["recipient"]["id"], self.identity.username)

    def test_send_message_fails_cleanly_if_no_instagram_identity(self):
        """If customer has no Instagram identity, return 400 without calling Meta API."""
        self.identity.delete()

        url = f"/api/v1/leads/{self.lead.id}/messages/"
        payload = {"message": "Hello!"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "no_instagram_identity")

    def test_send_message_rejects_mock_user_id(self):
        """If customer identity contains dummy 'USER_A', reject before calling Meta."""
        self.identity.external_user_id = "USER_A"
        self.identity.save()

        url = f"/api/v1/leads/{self.lead.id}/messages/"
        payload = {"message": "Hello!"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "invalid_recipient_id")

    def test_send_message_blocked_outside_24h_window(self):
        """Outbound message must be blocked if >24 hours have elapsed since last inbound message."""
        # Age the inbound message to 25 hours ago
        Message.objects.filter(id=self.inbound_msg.id).update(
            created_at=timezone.now() - timedelta(hours=25)
        )

        url = f"/api/v1/leads/{self.lead.id}/messages/"
        payload = {"message": "Hello outside window!"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("error_code"), "messaging_window_closed")

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_send_booking_link_uses_igsid(self, mock_post):
        """Send booking link must use IGSID and generate valid link."""
        mock_post.return_value = {"message_id": "mid_booking_link_777"}

        url = f"/api/v1/leads/{self.lead.id}/send-booking-link/"
        payload = {"message": "Here is your booking link: {BOOKING_URL}"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_post.assert_called_once()
        endpoint, data = mock_post.call_args[0]
        self.assertEqual(endpoint, "me/messages")
        self.assertEqual(data["recipient"]["id"], self.valid_igsid)

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_meta_provider_error_translation(self, mock_post):
        """Provider must translate Meta error 100 on recipient[id] to clear message."""
        mock_post.side_effect = ProviderSendError(
            "Meta API error (100): Param recipient[id] must be a valid ID string",
            code=100,
        )

        provider = InstagramMessagingProvider()
        result = provider.send_text_message(recipient_id="123456", text="Hello")

        self.assertFalse(result.success)
        self.assertIn("customer's Instagram account ID is invalid", result.error_message)


class InstagramOutboundRegressionTests(TestCase):
    """
    Regression tests for Instagram outbound message pipeline.
    Validates that real IGSIDs are always persisted from inbound webhooks
    and that the outbound path never resolves to USER_A or other test values.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@v4studio.test",
            password="StrongPassword123!",
            full_name="Admin User",
        )
        self.client.force_authenticate(user=self.admin)

        self.service = PhotographyService.objects.create(
            name="Baby Portrait Session",
            slug="baby-portrait-regression",
            base_price=15000.00,
            duration_minutes=60,
            is_active=True,
        )

    def test_real_sender_id_is_persisted_from_instagram_webhook(self):
        """Real Instagram sender.id from Meta webhook MUST be stored in CustomerIdentity.external_user_id."""
        from apps.integrations.pipeline import InboundPipelineService
        from apps.integrations.meta.instagram.parser import InstagramInboundParser
        from apps.customers.models import CustomerIdentity

        REAL_IGSID = "987654321012345"
        payload = {
            "object": "instagram",
            "entry": [{
                "id": "PAGE_123",
                "time": 1723145678,
                "messaging": [{
                    "sender": {"id": REAL_IGSID},
                    "recipient": {"id": "BUSINESS_PAGE_123"},
                    "timestamp": 1723145678,
                    "message": {
                        "mid": "real_mid_abc123",
                        "text": "Hi, want to book a session",
                    },
                }],
            }],
        }

        parser = InstagramInboundParser()
        msgs = parser.parse_messages(payload)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].external_user_id, REAL_IGSID)

    def test_customer_identity_is_created_from_inbound_instagram_message(self):
        """CustomerIdentity must be created with the real IGSID when processing a new Instagram webhook."""
        from apps.conversations.services import ConversationService
        from apps.customers.models import CustomerIdentity

        REAL_IGSID = "112233445566778"

        ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": REAL_IGSID,
            "external_message_id": "mid_creation_test_001",
            "text": "I want to book a session",
            "message_type": "TEXT",
            "provider_timestamp": None,
        })

        identity = CustomerIdentity.objects.filter(
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        ).first()
        self.assertIsNotNone(identity, "CustomerIdentity must be created for the real IGSID")
        self.assertEqual(identity.external_user_id, REAL_IGSID)

    def test_existing_instagram_identity_is_reused(self):
        """Sending a second Instagram message must reuse existing CustomerIdentity (no duplicates)."""
        from apps.conversations.services import ConversationService
        from apps.customers.models import CustomerIdentity

        REAL_IGSID = "888777666555444"

        # First message
        ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": REAL_IGSID,
            "external_message_id": "mid_first_msg",
            "text": "Hello",
            "message_type": "TEXT",
        })

        # Second message from same sender
        ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": REAL_IGSID,
            "external_message_id": "mid_second_msg",
            "text": "What sessions do you offer?",
            "message_type": "TEXT",
        })

        identity_count = CustomerIdentity.objects.filter(
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        ).count()
        self.assertEqual(identity_count, 1, "Must reuse existing identity, not create duplicates")

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_outbound_message_uses_customer_identity_external_user_id(self, mock_post):
        """Outbound message must use CustomerIdentity.external_user_id (IGSID), never UUID or phone."""
        REAL_IGSID = "556677889900112"
        mock_post.return_value = {"message_id": "mid_out_test_999"}

        customer = Customer.objects.create(
            display_name="Test Customer",
            primary_phone="+919876543210",
        )
        identity = CustomerIdentity.objects.create(
            customer=customer,
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        )
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            text="Test message",
            external_message_id="mid_inbound_for_window",
            created_at=timezone.now(),
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Hello from admin!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_post.assert_called_once()
        _, call_data = mock_post.call_args[0]
        self.assertEqual(call_data["recipient"]["id"], REAL_IGSID)
        self.assertNotEqual(call_data["recipient"]["id"], str(customer.id))
        self.assertNotEqual(call_data["recipient"]["id"], str(lead.id))
        self.assertNotEqual(call_data["recipient"]["id"], customer.primary_phone)

    def test_user_a_cannot_be_used_in_production_outbound_messaging(self):
        """USER_A must always be rejected as a recipient by the provider."""
        provider = InstagramMessagingProvider()
        result = provider.send_text_message(recipient_id="USER_A", text="Hello")
        self.assertFalse(result.success)
        self.assertIn("Invalid Instagram recipient ID", result.error_message)

    def test_missing_instagram_identity_returns_structured_error(self):
        """Missing Instagram identity must return error_code=no_instagram_identity, not generic failure."""
        customer = Customer.objects.create(display_name="No Identity Customer")
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Hello!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "no_instagram_identity")
        self.assertIn("Instagram", response.data.get("message", ""))

    def test_closed_messaging_window_blocks_outbound_message(self):
        """Messaging window > 24h must return error_code=messaging_window_closed."""
        REAL_IGSID = "444333222111000"
        customer = Customer.objects.create(display_name="Window Closed Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        )
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        # Seed inbound message 25h ago (outside window)
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            text="Old message",
            external_message_id="mid_old_msg",
            provider_timestamp=timezone.now() - timedelta(hours=25),
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Hello!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("error_code"), "messaging_window_closed")

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_open_messaging_window_allows_outbound_message(self, mock_post):
        """Messaging window < 24h must allow outbound message."""
        REAL_IGSID = "333444555666777"
        mock_post.return_value = {"message_id": "mid_window_open_test"}

        customer = Customer.objects.create(display_name="Window Open Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        )
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        # Seed inbound message 5 minutes ago (inside window)
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            text="Recent message",
            external_message_id="mid_recent_msg",
            provider_timestamp=timezone.now() - timedelta(minutes=5),
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Hello inside window!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_successful_meta_response_marks_message_sent(self, mock_post):
        """Successful Meta API call must store message with delivery_status=SENT."""
        REAL_IGSID = "222333444555666"
        mock_post.return_value = {"message_id": "mid_sent_test_001"}

        customer = Customer.objects.create(display_name="Sent Status Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        )
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            text="Inbound trigger",
            external_message_id="mid_inbound_sent_test",
            provider_timestamp=timezone.now(),
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Sent!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        stored = Message.objects.filter(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
        ).first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.delivery_status, Message.DeliveryStatus.SENT)
        self.assertEqual(stored.external_message_id, "mid_sent_test_001")

    @patch("apps.integrations.meta.common.client.MetaGraphClient.post")
    def test_meta_failure_returns_502_and_persists_failed_message(self, mock_post):
        """Meta API failure must return 502 and MUST persist a message with delivery_status=FAILED."""
        REAL_IGSID = "111222333444555"
        mock_post.side_effect = ProviderSendError("Simulated Meta failure", code=500)

        customer = Customer.objects.create(display_name="Meta Failure Customer")
        CustomerIdentity.objects.create(
            customer=customer,
            channel="INSTAGRAM",
            external_user_id=REAL_IGSID,
        )
        conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            text="Trigger inbound",
            external_message_id="mid_fail_trigger",
            provider_timestamp=timezone.now(),
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            status=Lead.Status.NEW,
            service=self.service,
            conversation=conversation,
        )

        initial_msg_count = Message.objects.filter(
            conversation=conversation, direction=Message.Direction.OUTBOUND
        ).count()

        response = self.client.post(
            f"/api/v1/leads/{lead.id}/messages/",
            {"message": "Will fail!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data.get("error_code"), "send_failed")

        # OUTBOUND message MUST be persisted with FAILED status
        outbound_count = Message.objects.filter(
            conversation=conversation, direction=Message.Direction.OUTBOUND
        ).count()
        self.assertEqual(outbound_count, initial_msg_count + 1)
        
        failed_msg = Message.objects.filter(
            conversation=conversation, direction=Message.Direction.OUTBOUND
        ).latest("created_at")
        self.assertEqual(failed_msg.delivery_status, Message.DeliveryStatus.FAILED)
        self.assertEqual(failed_msg.raw_payload.get("error"), "Simulated Meta failure")

    def test_frontend_does_not_need_to_send_recipient_id(self):
        """
        The /leads/{id}/messages/ endpoint must resolve the recipient from the lead,
        NOT from any recipient_id field in the request body.
        """
        REAL_IGSID = "777888999000111"

        with patch("apps.integrations.meta.common.client.MetaGraphClient.post") as mock_post:
            mock_post.return_value = {"message_id": "mid_no_recipient_field_test"}

            customer = Customer.objects.create(display_name="Frontend Test Customer")
            CustomerIdentity.objects.create(
                customer=customer,
                channel="INSTAGRAM",
                external_user_id=REAL_IGSID,
            )
            conversation = Conversation.objects.create(customer=customer, channel="INSTAGRAM")
            Message.objects.create(
                conversation=conversation,
                direction=Message.Direction.INBOUND,
                text="Inbound",
                external_message_id="mid_frontend_test",
                provider_timestamp=timezone.now(),
            )
            lead = Lead.objects.create(
                customer=customer,
                source_channel="INSTAGRAM",
                status=Lead.Status.NEW,
                service=self.service,
                conversation=conversation,
            )

            # Frontend only sends {message: "..."}, NOT recipient_id
            response = self.client.post(
                f"/api/v1/leads/{lead.id}/messages/",
                {"message": "Hello!"},
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            # Verify the correct IGSID was used, NOT anything from the request
            _, call_data = mock_post.call_args[0]
            self.assertEqual(call_data["recipient"]["id"], REAL_IGSID)

