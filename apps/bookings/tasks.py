import logging
from celery import shared_task
from django.conf import settings
from apps.bookings.models import Booking
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider

logger = logging.getLogger("apps.bookings")

from django.db import transaction
from apps.notifications.models import Notification

@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_whatsapp(self, booking_id: str):
    """
    Asynchronously sends a WhatsApp booking confirmation message.
    Retries up to 3 times on transient failures.
    Uses Notification model for idempotency and status tracking.
    """
    try:
        booking = Booking.objects.select_related("customer", "service", "package").get(id=booking_id)
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found for WhatsApp confirmation.")
        return

    # Skip if phone number is not available
    if not booking.customer.primary_phone:
        logger.warning(f"Booking {booking_id} has no customer phone number. Cannot send WhatsApp confirmation.")
        return

    idempotency_key = f"booking_conf_{booking_id}"
    
    with transaction.atomic():
        # Get or create notification record
        notification, created = Notification.objects.select_for_update().get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "customer": booking.customer,
                "channel": Notification.Channel.WHATSAPP,
                "notification_type": Notification.NotificationType.BOOKING_CONFIRMATION,
                "status": Notification.Status.PENDING,
            }
        )
        
        # If not pending/failed (and not permanent error), we shouldn't send
        if notification.status in [Notification.Status.SENT, Notification.Status.DELIVERED, Notification.Status.READ]:
            logger.info(f"Booking confirmation {booking_id} already sent (Status: {notification.status}). Skipping.")
            return
            
        if notification.status == Notification.Status.FAILED and notification.is_permanent_error:
            logger.info(f"Booking confirmation {booking_id} previously failed permanently. Skipping.")
            return

        # Record retry attempt if it's not the first try
        if not created and notification.status == Notification.Status.FAILED:
            notification.retry_count += 1
            notification.status = Notification.Status.PENDING
            notification.save(update_fields=["retry_count", "status", "updated_at"])

    try:
        provider = WhatsAppMessagingProvider()
        
        starts_at_formatted = booking.starts_at.astimezone().strftime("%A, %B %d, %Y at %I:%M %p")
        service_name = booking.package.name if booking.package else booking.service.name
        
        result = provider.send_booking_confirmation_message(
            recipient_id=booking.customer.primary_phone,
            customer_name=booking.customer.display_name or "Valued Client",
            service_name=service_name,
            starts_at=starts_at_formatted
        )
        
        if result.success:
            logger.info(f"Successfully sent WhatsApp confirmation for booking {booking_id}")
            notification.mark_sent(external_message_id=result.external_message_id or "")
        else:
            logger.error(f"Failed to send WhatsApp confirmation for booking {booking_id}: {result.error_message}")
            # Determine if error is permanent (e.g. invalid phone number vs network issue)
            # For this example, we treat Auth/Configuration errors as permanent to avoid spamming
            error_msg = str(result.error_message).lower()
            is_permanent = "not configured" in error_msg or "invalid format" in error_msg
            
            notification.mark_failed(error_message=result.error_message or "Unknown provider error", is_permanent=is_permanent)
            
            if not is_permanent:
                raise Exception(result.error_message)
            
    except Exception as e:
        logger.error(f"Error in send_booking_confirmation_whatsapp task: {str(e)}")
        # Only mark failed if we haven't already marked it in the if block above
        if notification.status != Notification.Status.FAILED:
             notification.mark_failed(error_message=str(e), is_permanent=False)
             
        # Retry with exponential backoff
        self.retry(exc=e, countdown=2 ** self.request.retries * 60)
