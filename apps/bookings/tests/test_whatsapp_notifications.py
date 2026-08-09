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
        self.customer = Customer.objects.create(
            display_name="Test User",
            primary_phone="+1234567890",
        )
        self.service = PhotographyService.objects.create(
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

    @patch("apps.bookings.tasks.WhatsAppMessagingProvider")
    def test_successful_notification_creates_record(self, MockProvider):
        # Setup mock
        mock_provider_instance = MockProvider.return_value
        mock_provider_instance.send_booking_confirmation_message.return_value = OutboundResult(
            success=True,
            external_message_id="wamid.12345",
            provider_response={}
        )

        # Execute task
        send_booking_confirmation_whatsapp(self.booking.id)

        # Verify Notification was created and marked SENT
        notification = Notification.objects.get(idempotency_key=f"booking_conf_{self.booking.id}")
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertEqual(notification.external_message_id, "wamid.12345")
        self.assertEqual(notification.notification_type, Notification.NotificationType.BOOKING_CONFIRMATION)

    @patch("apps.bookings.tasks.WhatsAppMessagingProvider")
    def test_idempotency_prevents_duplicate_send(self, MockProvider):
        # Create a notification that is already SENT
        Notification.objects.create(
            idempotency_key=f"booking_conf_{self.booking.id}",
            customer=self.customer,
            channel=Notification.Channel.WHATSAPP,
            notification_type=Notification.NotificationType.BOOKING_CONFIRMATION,
            status=Notification.Status.SENT,
            external_message_id="wamid.existing"
        )

        mock_provider_instance = MockProvider.return_value

        # Execute task
        send_booking_confirmation_whatsapp(self.booking.id)

        # Verify provider was NOT called
        mock_provider_instance.send_booking_confirmation_message.assert_not_called()

    @patch("apps.bookings.tasks.WhatsAppMessagingProvider")
    @patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.retry")
    def test_transient_failure_retries_and_marks_failed(self, mock_retry, MockProvider):
        # Setup mock for failure
        mock_provider_instance = MockProvider.return_value
        mock_provider_instance.send_booking_confirmation_message.return_value = OutboundResult(
            success=False,
            error_message="Connection timeout"
        )
        
        # We must configure retry to raise an exception to simulate Celery aborting the current execution frame
        mock_retry.side_effect = Exception("Retry triggered")

        # Execute task
        with self.assertRaises(Exception) as context:
            send_booking_confirmation_whatsapp(self.booking.id)
            
        self.assertTrue("Retry triggered" in str(context.exception))

        # Verify Notification was marked FAILED, but not permanent
        notification = Notification.objects.get(idempotency_key=f"booking_conf_{self.booking.id}")
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertFalse(notification.is_permanent_error)
        self.assertEqual(notification.error_message, "Connection timeout")
        mock_retry.assert_called_once()
        
    @patch("apps.bookings.tasks.WhatsAppMessagingProvider")
    @patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.retry")
    def test_permanent_failure_halts_retries(self, mock_retry, MockProvider):
        # Setup mock for permanent failure
        mock_provider_instance = MockProvider.return_value
        mock_provider_instance.send_booking_confirmation_message.return_value = OutboundResult(
            success=False,
            error_message="WHATSAPP_PHONE_NUMBER_ID is not configured in settings."
        )

        # Execute task
        send_booking_confirmation_whatsapp(self.booking.id)

        # Verify Notification was marked FAILED and permanent
        notification = Notification.objects.get(idempotency_key=f"booking_conf_{self.booking.id}")
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertTrue(notification.is_permanent_error)
        
        # Verify retry was NOT called
        mock_retry.assert_not_called()
