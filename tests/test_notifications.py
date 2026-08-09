"""
Comprehensive tests for Notifications orchestration module.
Tests idempotency, provider selection, domain notification helpers, transient retries,
permanent error handling, webhook status synchronization, and admin APIs.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
from apps.customers.models import Customer, CustomerIdentity
from apps.integrations.meta.base import OutboundResult
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.notifications.models import Notification
from apps.notifications.services import (
    NotificationService,
    PermanentNotificationError,
    TransientNotificationError,
)
from apps.notifications.tasks import dispatch_notification_task
from apps.services.models import PhotographyService


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="studio_admin@v4studio.com",
        password="AdminSecurePassword123!",
        full_name="Studio Admin",
    )


@pytest.fixture
def wa_customer():
    cust = Customer.objects.create(display_name="Sarah Jenkins", email="sarah@example.com")
    CustomerIdentity.objects.create(
        customer=cust,
        channel=CustomerIdentity.Channel.WHATSAPP,
        external_user_id="919876543210",
    )
    return cust


@pytest.fixture
def ig_customer():
    cust = Customer.objects.create(display_name="Michael Scott", email="michael@example.com")
    CustomerIdentity.objects.create(
        customer=cust,
        channel=CustomerIdentity.Channel.INSTAGRAM,
        external_user_id="ig_user_102030",
    )
    return cust


@pytest.fixture
def photography_service():
    return PhotographyService.objects.create(
        name="Maternity Portrait Session",
        slug="maternity-portrait-session",
        duration_minutes=60,
        base_price=350.00,
    )


@pytest.fixture
def test_booking(wa_customer, photography_service):
    starts_at = timezone.now() + timedelta(days=2)
    ends_at = starts_at + timedelta(minutes=60)
    return Booking.objects.create(
        customer=wa_customer,
        service=photography_service,
        starts_at=starts_at,
        ends_at=ends_at,
        status=Booking.Status.CONFIRMED,
    )


@pytest.mark.django_db
class TestNotificationIdempotency:
    """Tests idempotency key deduplication to prevent duplicate message sends."""

    @patch.object(WhatsAppMessagingProvider, "send_booking_link_message")
    def test_idempotent_duplicate_call_returns_existing_record_without_resend(
        self, mock_send, wa_customer
    ):
        mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.IDEMP_1")

        # 1st Call
        notif1, was_created1 = NotificationService.send_notification(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="BOOKING_LINK",
            context={"booking_url": "https://studio.com/book/link1"},
            idempotency_key="idemp_key_booking_lead_99",
            async_delivery=False,
        )
        assert was_created1 is True
        assert notif1.status == Notification.Status.SENT
        assert notif1.external_message_id == "wamid.IDEMP_1"
        assert mock_send.call_count == 1

        # 2nd Call (duplicate idempotency key)
        notif2, was_created2 = NotificationService.send_notification(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="BOOKING_LINK",
            context={"booking_url": "https://studio.com/book/link1"},
            idempotency_key="idemp_key_booking_lead_99",
            async_delivery=False,
        )
        assert was_created2 is False
        assert notif2.id == notif1.id
        # Ensure provider was NOT called a second time
        assert mock_send.call_count == 1


@pytest.mark.django_db
class TestNotificationProviderRouting:
    """Tests provider routing for Instagram vs WhatsApp channels."""

    @patch.object(InstagramMessagingProvider, "send_booking_link_message")
    def test_routes_to_instagram_provider(self, mock_ig_send, ig_customer):
        mock_ig_send.return_value = OutboundResult(success=True, external_message_id="ig_mid_555")

        notif, _ = NotificationService.send_booking_link(
            customer=ig_customer,
            channel="INSTAGRAM",
            booking_url="https://studio.com/book/ig_token",
            service_name="Fashion Shoot",
            async_delivery=False,
        )

        assert notif.status == Notification.Status.SENT
        assert notif.external_message_id == "ig_mid_555"
        mock_ig_send.assert_called_once_with(
            recipient_id="ig_user_102030",
            booking_url="https://studio.com/book/ig_token",
            customer_name="Michael Scott",
            service_name="Fashion Shoot",
        )

    @patch.object(WhatsAppMessagingProvider, "send_booking_link_message")
    def test_routes_to_whatsapp_provider(self, mock_wa_send, wa_customer):
        mock_wa_send.return_value = OutboundResult(success=True, external_message_id="wamid.WA_LINK_77")

        notif, _ = NotificationService.send_booking_link(
            customer=wa_customer,
            channel="WHATSAPP",
            booking_url="https://studio.com/book/wa_token",
            service_name="Newborn Shoot",
            async_delivery=False,
        )

        assert notif.status == Notification.Status.SENT
        assert notif.external_message_id == "wamid.WA_LINK_77"
        mock_wa_send.assert_called_once()


@pytest.mark.django_db
class TestDomainNotificationHelpers:
    """Tests domain notification helpers (confirmation, reminder, cancellation)."""

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_send_booking_confirmation(self, mock_send, test_booking):
        mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.CONFIRM_1")

        notif, created = NotificationService.send_booking_confirmation(
            booking=test_booking,
            async_delivery=False,
        )

        assert created is True
        assert notif.notification_type == Notification.NotificationType.BOOKING_CONFIRMATION
        assert notif.status == Notification.Status.SENT
        assert "CONFIRMED" in notif.rendered_text
        assert "Maternity Portrait Session" in notif.rendered_text
        mock_send.assert_called_once()

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_send_booking_reminder(self, mock_send, test_booking):
        mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.REMINDER_1")

        notif, created = NotificationService.send_booking_reminder(
            booking=test_booking,
            async_delivery=False,
        )

        assert created is True
        assert notif.notification_type == Notification.NotificationType.BOOKING_REMINDER
        assert "Friendly reminder" in notif.rendered_text
        assert notif.status == Notification.Status.SENT

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_send_booking_cancellation(self, mock_send, test_booking):
        mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.CANCEL_1")

        notif, created = NotificationService.send_booking_cancellation(
            booking=test_booking,
            reason="Customer request due to travel",
            reschedule_url="https://studio.com/book/reschedule123",
            async_delivery=False,
        )

        assert created is True
        assert notif.notification_type == Notification.NotificationType.BOOKING_CANCELLATION
        assert "has been cancelled" in notif.rendered_text
        assert "Customer request due to travel" in notif.rendered_text
        assert "https://studio.com/book/reschedule123" in notif.rendered_text


@pytest.mark.django_db
class TestTransientRetryAndPermanentErrorHandling:
    """Tests error categorization: transient failures retry, permanent failures halt immediately."""

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_permanent_error_marks_failed_and_halts_retries(self, mock_send, wa_customer):
        # 131026 = WhatsApp user number out of service / invalid
        mock_send.return_value = OutboundResult(
            success=False,
            error_message="Meta API Error 131026: Message undeliverable to recipient phone",
        )

        with pytest.raises(PermanentNotificationError):
            NotificationService.send_notification(
                customer=wa_customer,
                channel="WHATSAPP",
                notification_type="GENERAL",
                context={"text": "Hello"},
                async_delivery=False,
            )

        notif = Notification.objects.filter(customer=wa_customer).first()
        assert notif.status == Notification.Status.FAILED
        assert notif.is_permanent_error is True
        assert "131026" in notif.error_message

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_transient_error_raises_transient_exception_for_celery_retry(self, mock_send, wa_customer):
        # 503 Server Gateway Timeout
        mock_send.return_value = OutboundResult(
            success=False,
            error_message="Connection timed out to Meta Graph API 503",
        )

        with pytest.raises(TransientNotificationError):
            NotificationService.send_notification(
                customer=wa_customer,
                channel="WHATSAPP",
                notification_type="GENERAL",
                context={"text": "Hello"},
                async_delivery=False,
            )

        notif = Notification.objects.filter(customer=wa_customer).first()
        assert notif.status == Notification.Status.FAILED
        assert notif.is_permanent_error is False
        assert notif.retry_count == 1


@pytest.mark.django_db
class TestStatusLifecycleSynchronization:
    """Tests webhook status updates syncing to Notification records."""

    def test_webhook_updates_notification_status_delivered_and_read(self, wa_customer):
        notif = Notification.objects.create(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="BOOKING_LINK",
            status=Notification.Status.SENT,
            external_message_id="wamid.SYNC_STATUS_999",
            sent_at=timezone.now(),
        )

        # 1. Simulate DELIVERED webhook
        NotificationService.update_status_by_external_id(
            external_message_id="wamid.SYNC_STATUS_999",
            delivery_status="DELIVERED",
        )
        notif.refresh_from_db()
        assert notif.status == Notification.Status.DELIVERED
        assert notif.delivered_at is not None

        # 2. Simulate READ webhook
        NotificationService.update_status_by_external_id(
            external_message_id="wamid.SYNC_STATUS_999",
            delivery_status="READ",
        )
        notif.refresh_from_db()
        assert notif.status == Notification.Status.READ
        assert notif.read_at is not None


@pytest.mark.django_db
class TestNotificationAdminAPI:
    """Tests Admin REST APIs for notifications monitoring and manual retry."""

    def setup_method(self):
        self.client = APIClient()

    def test_list_notifications_with_filters(self, admin_user, wa_customer, ig_customer):
        self.client.force_authenticate(user=admin_user)

        n1 = Notification.objects.create(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="BOOKING_CONFIRMATION",
            status=Notification.Status.SENT,
        )
        n2 = Notification.objects.create(
            customer=ig_customer,
            channel="INSTAGRAM",
            notification_type="BOOKING_LINK",
            status=Notification.Status.FAILED,
        )

        url = reverse("api_v1:notifications:notification-list")
        res = self.client.get(url, {"channel": "WHATSAPP"})
        assert res.status_code == status.HTTP_200_OK
        data = res.data.get("results", res.data)
        assert len(data) == 1
        assert data[0]["id"] == str(n1.id)

    def test_manual_retry_endpoint(self, admin_user, wa_customer):
        self.client.force_authenticate(user=admin_user)

        notif = Notification.objects.create(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="BOOKING_REMINDER",
            status=Notification.Status.FAILED,
            is_permanent_error=True,
            rendered_text="Your session is tomorrow",
        )

        with patch.object(WhatsAppMessagingProvider, "send_text_message") as mock_send:
            mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.RETRY_SUCCESS_1")

            url = reverse("api_v1:notifications:notification-retry", kwargs={"pk": notif.id})
            res = self.client.post(url)

            assert res.status_code == status.HTTP_200_OK
            assert res.data["status"] == "SENT"
            assert res.data["external_message_id"] == "wamid.RETRY_SUCCESS_1"
            assert res.data["is_permanent_error"] is False


@pytest.mark.django_db
class TestNotificationCeleryTasks:
    """Tests Celery task execution, handling of permanent vs transient failure in worker context."""

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_celery_task_success_execution(self, mock_send, wa_customer):
        mock_send.return_value = OutboundResult(success=True, external_message_id="wamid.CELERY_OK_1")

        notif = Notification.objects.create(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="GENERAL",
            status=Notification.Status.PENDING,
            rendered_text="Welcome to V4 Studio!",
        )

        res = dispatch_notification_task(str(notif.id))
        assert res["success"] is True
        assert res["external_message_id"] == "wamid.CELERY_OK_1"
        notif.refresh_from_db()
        assert notif.status == Notification.Status.SENT

    @patch.object(WhatsAppMessagingProvider, "send_text_message")
    def test_celery_task_permanent_error_halts_without_retry(self, mock_send, wa_customer):
        mock_send.return_value = OutboundResult(
            success=False,
            error_message="Recipient phone number invalid: 131026",
        )

        notif = Notification.objects.create(
            customer=wa_customer,
            channel="WHATSAPP",
            notification_type="GENERAL",
            status=Notification.Status.PENDING,
            rendered_text="Welcome to V4 Studio!",
        )

        res = dispatch_notification_task(str(notif.id))
        assert res["success"] is False
        assert res["permanent_error"] is True
        notif.refresh_from_db()
        assert notif.status == Notification.Status.FAILED
        assert notif.is_permanent_error is True
