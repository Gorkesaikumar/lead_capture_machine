from celery import shared_task
from apps.bookings.models import Booking
from apps.notifications.services import NotificationService


@shared_task(bind=True, max_retries=0)
def send_booking_confirmation_whatsapp(self, booking_id):
    booking = Booking.objects.select_related("customer", "service", "package").filter(pk=booking_id).first()
    if not booking:
        return {"status": "NOT_FOUND"}
    notification, _ = NotificationService.send_booking_confirmation(booking, channel="WHATSAPP", async_delivery=False)
    return {"status": notification.status, "notification_id": str(notification.pk)}
