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




@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.integrations.send_whatsapp_message_task",
)
def send_whatsapp_message_task(self, recipient_phone: str, text: str, local_message_id: str):
    """
    Asynchronously sends a standard text message via WhatsApp Cloud API.
    """
    from apps.conversations.models import Message
    with transaction.atomic():
        msg = Message.objects.select_for_update(of=("self",)).filter(external_message_id=local_message_id).first()
        if not msg:
            logger.error("Message %s not found for dispatch", local_message_id)
            raise self.retry(exc=Exception("Message not found"), countdown=5 * (2 ** self.request.retries))
            
        if msg.external_message_id != local_message_id:
            logger.info("Message %s already sent (id=%s). Skipping.", local_message_id, msg.external_message_id)
            return {"success": True, "external_message_id": msg.external_message_id}

        provider = WhatsAppMessagingProvider()
        res = provider.send_text_message(recipient_id=recipient_phone, text=text)
        if not res.success:
            logger.warning("WhatsApp send_text_message failed for %s: %s", recipient_phone, res.error_message)
            raise self.retry(exc=Exception(res.error_message), countdown=5 * (2 ** self.request.retries))
            
        ConversationService.update_message_delivery_status(
            external_message_id=local_message_id,
            delivery_status="SENT"
        )
        msg.external_message_id = res.external_message_id
        msg.save(update_fields=["external_message_id", "updated_at"])
        
    return {"success": True, "external_message_id": res.external_message_id}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.integrations.send_whatsapp_booking_link_task",
)
def send_whatsapp_booking_link_task(
    self,
    recipient_phone: str,
    booking_url: str,
    customer_name: Optional[str] = None,
    service_name: Optional[str] = None,
    force_template: bool = False,
):
    """
    Asynchronously sends a booking link via WhatsApp Cloud API.
    Automatically selects free-form message or approved Template depending on the 24h customer service window.
    """
    provider = WhatsAppMessagingProvider()
    res = provider.send_booking_link_message(
        recipient_id=recipient_phone,
        booking_url=booking_url,
        customer_name=customer_name,
        service_name=service_name,
        force_template=force_template,
    )
    if not res.success:
        logger.warning("WhatsApp send_booking_link failed for %s: %s", recipient_phone, res.error_message)
        raise self.retry(exc=Exception(res.error_message))
    return {"success": True, "external_message_id": res.external_message_id}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.integrations.send_instagram_message_task",
)
def send_instagram_message_task(self, recipient_id: str, text: str, local_message_id: str):
    """
    Asynchronously sends a standard text message via Instagram Graph API.
    """
    from apps.conversations.models import Message
    with transaction.atomic():
        msg = Message.objects.select_for_update(of=("self",)).filter(external_message_id=local_message_id).first()
        if not msg:
            logger.error("Message %s not found for dispatch", local_message_id)
            raise self.retry(exc=Exception("Message not found"), countdown=5 * (2 ** self.request.retries))
            
        if msg.external_message_id != local_message_id:
            logger.info("Message %s already sent (id=%s). Skipping.", local_message_id, msg.external_message_id)
            return {"success": True, "external_message_id": msg.external_message_id}

        provider = InstagramMessagingProvider()
        res = provider.send_text_message(recipient_id=recipient_id, text=text)
        
        if res.success and res.external_message_id:
            ConversationService.update_message_delivery_status(
                external_message_id=local_message_id,
                delivery_status="SENT"
            )
            msg.external_message_id = res.external_message_id
            msg.save(update_fields=["external_message_id", "updated_at"])
            return {"success": True, "external_message_id": res.external_message_id}
        else:
            error_msg = res.error_message or ""
            is_retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            if is_retryable:
                logger.warning("Instagram send_text_message rate limited/timeout for %s: %s. Retrying...", recipient_id, error_msg)
                raise self.retry(exc=Exception(res.error_message), countdown=5 * (2 ** self.request.retries))
            
            logger.error("Instagram send_text_message permanent failure for %s: %s", recipient_id, error_msg)
            ConversationService.update_message_delivery_status(
                external_message_id=local_message_id,
                delivery_status="FAILED",
                error_details={"error": error_msg}
            )
            return {"success": False, "error_message": error_msg}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="apps.integrations.send_instagram_media_message_task",
)
def send_instagram_media_message_task(self, recipient_id: str, media_url: str, media_type: str, caption: str, local_message_id: str):
    """
    Asynchronously sends a media message via Instagram Graph API.
    """
    from apps.conversations.models import Message
    with transaction.atomic():
        msg = Message.objects.select_for_update(of=("self",)).filter(external_message_id=local_message_id).first()
        if not msg:
            logger.error("Message %s not found for dispatch", local_message_id)
            raise self.retry(exc=Exception("Message not found"), countdown=5 * (2 ** self.request.retries))
            
        if msg.external_message_id != local_message_id:
            logger.info("Message %s already sent (id=%s). Skipping.", local_message_id, msg.external_message_id)
            return {"success": True, "external_message_id": msg.external_message_id}

        provider = InstagramMessagingProvider()
        res = provider.send_media_message(
            recipient_id=recipient_id,
            media_url=media_url,
            media_type=media_type,
            caption=caption,
        )
        
        if res.success and res.external_message_id:
            ConversationService.update_message_delivery_status(
                external_message_id=local_message_id,
                delivery_status="SENT"
            )
            msg.external_message_id = res.external_message_id
            msg.save(update_fields=["external_message_id", "updated_at"])
            return {"success": True, "external_message_id": res.external_message_id}
        else:
            error_msg = res.error_message or ""
            is_retryable = "rate limit" in error_msg.lower() or "timeout" in error_msg.lower()
            if is_retryable:
                logger.warning("Instagram send_media_message rate limited/timeout for %s: %s. Retrying...", recipient_id, error_msg)
                raise self.retry(exc=Exception(res.error_message), countdown=5 * (2 ** self.request.retries))
                
            logger.error("Instagram send_media_message permanent failure for %s: %s", recipient_id, error_msg)
            ConversationService.update_message_delivery_status(
                external_message_id=local_message_id,
                delivery_status="FAILED",
                error_details={"error": error_msg}
            )
            return {"success": False, "error_message": error_msg}
