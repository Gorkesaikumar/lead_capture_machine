from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings

from apps.bookings.models import Booking
from apps.customers.models import Customer
from apps.services.models import PhotographyService
from apps.notifications.models import Notification
from apps.bookings.tasks import send_booking_confirmation_whatsapp
from apps.integrations.meta.base import OutboundResult


class WhatsAppBookingNotificationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(organization=test_workspace(),
            display_name="Test User",
            primary_phone="+1234567890",
        )
        from tests.tenant_fixtures import configure_channel
        from apps.customers.models import CustomerIdentity
        from apps.conversations.models import Conversation, Message
        configure_channel(channel="WHATSAPP")
        CustomerIdentity.objects.create(customer=self.customer, channel="WHATSAPP", external_user_id="1234567890")
        conv = Conversation.objects.create(organization=self.customer.organization, customer=self.customer, channel="WHATSAPP")
        Message.objects.create(conversation=conv, direction="INBOUND", text="Hi", provider_timestamp=timezone.now())
        self.service = PhotographyService.objects.create(organization=test_workspace(),
            name="Test Service",
            base_price=500,
            duration_minutes=60,
            is_active=True,
        )
        
        studio_tz = ZoneInfo(getattr(settings, "TIME_ZONE", "UTC"))
        starts_at = timezone.now().astimezone(studio_tz) + timedelta(days=2)
        
        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=60),
            blocked_starts_at=starts_at,
            blocked_ends_at=starts_at + timedelta(minutes=60),
            status=Booking.Status.CONFIRMED,
        )

    @patch("apps.conversations.outbound.WhatsAppMessagingProvider.send_text_message")
    def test_successful_notification_creates_record(self, send):
        send.return_value = OutboundResult(success=True, external_message_id="wamid.booking-confirmed")
        result = send_booking_confirmation_whatsapp(self.booking.pk)
        self.assertEqual(result["status"], "SENT")
        self.assertEqual(Notification.objects.get().external_message_id, "wamid.booking-confirmed")

    @patch("apps.conversations.outbound.WhatsAppMessagingProvider.send_text_message")
    def test_idempotency_prevents_duplicate_send(self, send):
        send.return_value = OutboundResult(success=True, external_message_id="wamid.booking-once")
        send_booking_confirmation_whatsapp(self.booking.pk)
        send_booking_confirmation_whatsapp(self.booking.pk)
        send.assert_called_once()
        self.assertEqual(Notification.objects.count(), 1)

    @patch("apps.conversations.outbound.WhatsAppMessagingProvider.send_text_message")
    def test_timeout_is_retained_without_automatic_resend(self, send):
        send.return_value = OutboundResult(success=False, error_message="Network timeout")
        result = send_booking_confirmation_whatsapp(self.booking.pk)
        self.assertEqual(result["status"], "FAILED")
        send_booking_confirmation_whatsapp(self.booking.pk)
        send.assert_called_once()
        self.assertIn("response was not received", Notification.objects.get().error_message)

    @patch("apps.conversations.outbound.WhatsAppMessagingProvider.send_text_message")
    def test_missing_channel_blocks_provider_call(self, send):
        from apps.integrations.models import IntegrationConfig
        IntegrationConfig.objects.all().delete()
        result = send_booking_confirmation_whatsapp(self.booking.pk)
        self.assertEqual(result["status"], "FAILED")
        send.assert_not_called()
