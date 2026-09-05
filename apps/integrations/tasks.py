"""
Celery asynchronous tasks for Meta webhook event processing and outbound messaging.
"""
import logging
from typing import Optional
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.models import RawWebhookEvent
from apps.integrations.pipeline import InboundPipelineService
from apps.conversations.services import ConversationService
from apps.core.logging import PipelineLogger, PipelineStage

logger = logging.getLogger("apps.integrations.tasks")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="apps.integrations.process_instagram_webhook_event_task",
)
def process_instagram_webhook_event_task(self, raw_event_id: str):
    """
    Asynchronously processes a received Instagram RawWebhookEvent.
    """
    plog = PipelineLogger(
        base_logger=logger,
        task_id=self.request.id,
        channel="INSTAGRAM",
    )
    plog.info(
        PipelineStage.TASK_START,
        "Starting async processing for Instagram RawWebhookEvent",
        raw_event_id=raw_event_id,
        retry_count=self.request.retries,
    )

    try:
        with transaction.atomic():
            try:
                event = (
                    RawWebhookEvent.objects.select_for_update(of=("self",))
                    .get(id=raw_event_id)
                )
            except RawWebhookEvent.DoesNotExist:
                plog.error(
                    PipelineStage.TASK_FAILURE,
                    "RawWebhookEvent not found",
                    raw_event_id=raw_event_id,
                )
                return {"error": "Event not found"}

            plog.set(event_id=event.event_id)

            if event.status in [RawWebhookEvent.Status.PROCESSED, RawWebhookEvent.Status.DUPLICATE]:
                plog.info(
                    PipelineStage.TASK_SUCCESS,
                    "RawWebhookEvent already processed — skipping",
                    existing_status=event.status,
                )
                return {"status": event.status}

            event.status = RawWebhookEvent.Status.PROCESSING
            event.save(update_fields=["status", "updated_at"])

        result = InboundPipelineService.process_raw_webhook_event(event, plog=plog)

        with transaction.atomic():
            event = RawWebhookEvent.objects.select_for_update(of=("self",)).get(id=raw_event_id)
            event.status = RawWebhookEvent.Status.PROCESSED
            event.messages_count = result.get("messages_processed", 0)
            event.processed_at = timezone.now()
            event.save(update_fields=["status", "messages_count", "processed_at", "updated_at"])

        plog.info(
            PipelineStage.TASK_SUCCESS,
            "Instagram RawWebhookEvent processed successfully",
            messages_processed=result.get("messages_processed", 0),
            leads_created=result.get("leads_created", 0),
            new_messages_created=result.get("new_messages_created", 0),
        )
        return result

    except Exception as exc:
        plog.exception(
            PipelineStage.TASK_FAILURE,
            "Failed to process Instagram RawWebhookEvent",
            raw_event_id=raw_event_id,
            retry_count=self.request.retries,
        )
        try:
            with transaction.atomic():
                event = RawWebhookEvent.objects.select_for_update(of=("self",)).get(id=raw_event_id)
                event.status = RawWebhookEvent.Status.FAILED
                event.error_message = str(exc)
                event.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass

        retry_delay = 5 * (2 ** self.request.retries)
        plog.warning(
            PipelineStage.TASK_RETRY,
            "Scheduling retry for Instagram processing task",
            retry_count=self.request.retries,
            retry_delay_seconds=retry_delay,
        )
        raise self.retry(exc=exc, countdown=retry_delay)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="apps.integrations.process_whatsapp_webhook_event_task",
)
def process_whatsapp_webhook_event_task(self, raw_event_id: str):
    """
    Asynchronously processes a received WhatsApp RawWebhookEvent:
    1. Normalizes messages and parses delivery status updates.
    2. Idempotently updates customer, conversation, and message records.
    3. Triggers LeadDetectionService on newly created customer messages.
    4. Updates delivery status (sent, delivered, read, failed) on existing messages.
    5. Updates RawWebhookEvent lifecycle status to PROCESSED.
    """
    plog = PipelineLogger(
        base_logger=logger,
        task_id=self.request.id,
        channel="WHATSAPP",
    )
    plog.info(
        PipelineStage.TASK_START,
        "Starting async processing for WhatsApp RawWebhookEvent",
        raw_event_id=raw_event_id,
        retry_count=self.request.retries,
    )

    try:
        with transaction.atomic():
            try:
                event = (
                    RawWebhookEvent.objects.select_for_update(of=("self",))
                    .get(id=raw_event_id)
                )
            except RawWebhookEvent.DoesNotExist:
                plog.error(
                    PipelineStage.TASK_FAILURE,
                    "RawWebhookEvent not found",
                    raw_event_id=raw_event_id,
                )
                return {"error": "Event not found"}

            plog.set(event_id=event.event_id)

            if event.status in [RawWebhookEvent.Status.PROCESSED, RawWebhookEvent.Status.DUPLICATE]:
                plog.info(
                    PipelineStage.TASK_SUCCESS,
                    "RawWebhookEvent already processed — skipping",
                    existing_status=event.status,
                )
                return {"status": event.status}

            event.status = RawWebhookEvent.Status.PROCESSING
            event.save(update_fields=["status", "updated_at"])

        result = InboundPipelineService.process_raw_webhook_event(event, plog=plog)

        with transaction.atomic():
            event = RawWebhookEvent.objects.select_for_update(of=("self",)).get(id=raw_event_id)
            event.status = RawWebhookEvent.Status.PROCESSED
            event.messages_count = result.get("messages_processed", 0) + result.get("statuses_processed", 0)
            event.processed_at = timezone.now()
            event.save(update_fields=["status", "messages_count", "processed_at", "updated_at"])

        plog.info(
            PipelineStage.TASK_SUCCESS,
            "WhatsApp RawWebhookEvent processed successfully",
            messages_processed=result.get("messages_processed", 0),
            statuses_processed=result.get("statuses_processed", 0),
            leads_created=result.get("leads_created", 0),
        )
        return result

    except Exception as exc:
        plog.exception(
            PipelineStage.TASK_FAILURE,
            "Failed to process WhatsApp RawWebhookEvent",
            raw_event_id=raw_event_id,
            retry_count=self.request.retries,
        )
        try:
            with transaction.atomic():
                event = RawWebhookEvent.objects.select_for_update(of=("self",)).get(id=raw_event_id)
                event.status = RawWebhookEvent.Status.FAILED
                event.error_message = str(exc)
                event.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass

        retry_delay = 5 * (2 ** self.request.retries)
        plog.warning(
            PipelineStage.TASK_RETRY,
            "Scheduling retry for WhatsApp processing task",
            retry_count=self.request.retries,
            retry_delay_seconds=retry_delay,
        )
        raise self.retry(exc=exc, countdown=retry_delay)




def _legacy_dispatch(local_message_id):
    from apps.conversations.models import Message
    from apps.conversations.outbound import dispatch_message
    message = Message.objects.filter(external_message_id=local_message_id).first()
    if not message:
        return {"success": False, "error": "Legacy message not found. Use the conversation send endpoint."}
    result = dispatch_message(str(message.pk))
    return {"success": result.delivery_status == "SENT", "external_message_id": result.external_message_id, "status": result.delivery_status}


@shared_task
def send_instagram_message_task(recipient_id, text, local_message_id):
    return _legacy_dispatch(local_message_id)


@shared_task
def send_whatsapp_message_task(recipient_phone, text, local_message_id):
    return _legacy_dispatch(local_message_id)


@shared_task
def send_instagram_media_message_task(recipient_id, media_url, media_type, caption, local_message_id):
    return _legacy_dispatch(local_message_id)


@shared_task
def send_whatsapp_booking_link_task(recipient_phone, booking_url, customer_name=None, service_name=None, force_template=False, conversation_id=None):
    # A phone number alone is not a tenant boundary.
    if not conversation_id:
        return {"success": False, "error": "A workspace-scoped conversation_id is required."}
    from apps.conversations.models import Conversation
    from apps.conversations.outbound import queue_message
    conversation = Conversation.objects.get(pk=conversation_id, channel="WHATSAPP")
    msg = queue_message(conversation, {"text": booking_url})
    return {"status": msg.delivery_status, "message_id": str(msg.pk)}


@shared_task(name="apps.integrations.recover_webhooks")
def recover_webhooks():
    from datetime import timedelta
    # Failed events remain inspectable; automatic recovery retries only recent failures.
    events = RawWebhookEvent.objects.filter(status__in=["PENDING", "PROCESSING", "FAILED"], updated_at__lt=timezone.now()-timedelta(minutes=2), created_at__gt=timezone.now()-timedelta(days=1))[:100]
    for event in events:
        task = process_whatsapp_webhook_event_task if event.channel == "WHATSAPP" else process_instagram_webhook_event_task
        task.delay(str(event.pk))

from .deletion import delete_instagram_data, recover_deletion_requests  # noqa: F401


@shared_task(name="apps.integrations.verify_connection")
def verify_connection(config_id):
    from .health_service import verify_integration
    verify_integration(config_id)


@shared_task(name="apps.integrations.check_connections")
def check_connections():
    from datetime import timedelta
    from .models import IntegrationConfig, OAuthAttempt
    for config_id in IntegrationConfig.objects.filter(is_active=True, organization__is_active=True, organization__is_deleted=False).values_list("pk", flat=True).iterator():
        verify_connection.delay(str(config_id))
    OAuthAttempt.objects.filter(expires_at__lt=timezone.now()-timedelta(days=1)).delete()
