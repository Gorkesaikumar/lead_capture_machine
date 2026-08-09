"""
Celery asynchronous tasks for outbound notification dispatch and retries.
"""
import logging
from celery import shared_task
from apps.notifications.services import (
    NotificationService,
    PermanentNotificationError,
    TransientNotificationError,
)

logger = logging.getLogger("apps.notifications.tasks")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.notifications.dispatch_notification_task",
)
def dispatch_notification_task(self, notification_id: str):
    """
    Asynchronously executes outbound notification dispatch.
    Implements bounded exponential backoff for transient failures (up to 3 retries: 5s, 10s, 20s)
    and immediately halts retries on permanent failures.
    """
    logger.info("Executing dispatch_notification_task for notification_id=%s (retry=%d)", notification_id, self.request.retries)

    try:
        notification = NotificationService.dispatch_now(notification_id)
        return {
            "success": True,
            "notification_id": str(notification.id),
            "status": notification.status,
            "external_message_id": notification.external_message_id,
        }

    except PermanentNotificationError as perm_exc:
        logger.error(
            "Permanent failure on notification_id=%s: %s. Halting retries.",
            notification_id,
            str(perm_exc),
        )
        return {
            "success": False,
            "notification_id": notification_id,
            "permanent_error": True,
            "error": str(perm_exc),
        }

    except (TransientNotificationError, Exception) as exc:
        retry_delay = 5 * (2 ** self.request.retries)
        logger.warning(
            "Transient failure on notification_id=%s: %s. Scheduling retry in %ds (retry %d/%d)",
            notification_id,
            str(exc),
            retry_delay,
            self.request.retries + 1,
            self.max_retries,
        )
        raise self.retry(exc=exc, countdown=retry_delay)
