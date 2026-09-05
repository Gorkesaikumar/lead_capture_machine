"""Durable outbound messages. Only provider acceptance may produce SENT.

SENDING is a durable claim. An interrupted/ambiguous send is never automatically
retried: Meta does not provide an exactly-once send contract for these requests.
"""
from datetime import timedelta
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError
from apps.conversations.models import Conversation, Message
from apps.integrations.models import IntegrationConfig
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider

logger = logging.getLogger(__name__)


class MessagingUnavailable(APIException):
    status_code = 409
    default_code = "configuration_required"


def configuration_status(config):
    if not config or not config.is_active:
        return "DISCONNECTED", "Connect this channel to start receiving and replying to messages."
    if not config.credentials.get("access_token") or not config.metadata.get("destination_id"):
        return "CONFIGURATION_REQUIRED", "Access token and destination account must be configured."
    metadata = config.metadata
    expires = metadata.get("token_expires_at")
    if expires:
        from django.utils.dateparse import parse_datetime
        expiry = parse_datetime(expires)
        if expiry and timezone.is_aware(expiry) and expiry <= timezone.now():
            return "TOKEN_EXPIRED", "The access token expired. Reconnect this channel."
    if metadata.get("error_code") in ("permission_required", "token_expired"):
        return metadata["error_code"].upper(), metadata.get("last_error", "Reconnect this channel.")
    if metadata.get("webhook_subscribed") is False:
        return "CONFIGURATION_REQUIRED", "Meta webhook subscription failed. Reconnect this channel."
    if metadata.get("error_code"):
        return "ERROR", metadata.get("last_error", "Connection verification failed. Check this channel again.")
    if metadata.get("last_verified_at"):
        from django.utils.dateparse import parse_datetime
        checked = parse_datetime(metadata["last_verified_at"])
        if not checked or checked < timezone.now()-timedelta(hours=24):
            return "CONFIGURED_UNVERIFIED", "Connection verification is overdue. Check the connection to refresh its status."
        return "CONNECTED", "Meta account access and webhook subscription verified."
    if metadata.get("last_accepted_at"):
        from django.utils.dateparse import parse_datetime
        accepted = parse_datetime(metadata["last_accepted_at"])
        if accepted and accepted > timezone.now()-timedelta(hours=24):
            return "CONNECTED", "Meta accepted an outbound message; delivery depends on provider callbacks."
    return "CONFIGURED_UNVERIFIED", "Credentials saved. Live sending and Meta permissions have not been verified."


def window_open(conversation):
    now = timezone.now()
    return conversation.messages.filter(
        direction="INBOUND", provider_timestamp__gt=now-timedelta(hours=24),
        provider_timestamp__lte=now,
    ).exists()


def validate_send(conversation, payload):
    if not conversation.organization_id or conversation.customer.organization_id != conversation.organization_id:
        raise MessagingUnavailable("Conversation workspace is invalid.")
    if conversation.channel not in ("INSTAGRAM", "WHATSAPP"):
        raise MessagingUnavailable("Website forms capture inquiries; no return messaging transport is configured.")
    config = IntegrationConfig.objects.filter(organization=conversation.organization, provider=conversation.channel).first()
    state, detail = configuration_status(config)
    if state not in ("CONNECTED", "CONFIGURED_UNVERIFIED"):
        raise MessagingUnavailable({"code": state.lower(), "message": detail})
    identity = conversation.customer.identities.filter(channel=conversation.channel, organization=conversation.organization).first()
    if not identity:
        raise MessagingUnavailable({"code": "missing_identity", "message": "No external contact identity exists for this conversation."})
    if conversation.channel == "INSTAGRAM":
        valid, error = InstagramMessagingProvider.validate_recipient_id(identity.external_user_id)
        if not valid:
            raise MessagingUnavailable({"code": "invalid_recipient_id", "message": error})
    if payload.get("template"):
        if conversation.channel != "WHATSAPP":
            raise ValidationError("Templates are only supported for WhatsApp.")
    elif not window_open(conversation):
        raise MessagingUnavailable({"code": "messaging_window_closed", "message": "The 24-hour messaging window is closed. WhatsApp requires an approved template; Instagram requires a new customer message."})
    return config, identity


def queue_message(conversation, payload, sender=None, request_id="", dispatch=True):
    with transaction.atomic():
        conversation = Conversation.objects.select_for_update(of=("self",)).select_related("customer", "organization").get(pk=conversation.pk)
        if request_id:
            existing = conversation.messages.filter(client_request_id=request_id).first()
            if existing:
                if existing.attachment_metadata.get("dispatch") != payload:
                    raise ValidationError("This request ID was already used for different content.")
                return existing
        validate_send(conversation, payload)
        message = Message.objects.create(
            conversation=conversation, direction="OUTBOUND", sender=sender,
            client_request_id=request_id, text=payload.get("text") or payload.get("caption") or "",
            message_type=payload.get("media_type", "TEXT") if payload.get("media_url") else "TEXT",
            delivery_status="QUEUED", attachment_metadata={"dispatch": payload},
        )
        if dispatch:
            transaction.on_commit(lambda: enqueue_dispatch(str(message.pk)))
    return message


def enqueue_dispatch(message_id):
    from apps.conversations.tasks import dispatch_message_task
    try:
        dispatch_message_task.delay(message_id)
    except Exception:
        # The committed QUEUED record is the outbox; the periodic drainer recovers it.
        logger.warning("Outbound queue unavailable; durable message awaits recovery", extra={"message_id": message_id})


def classify_error(error):
    error = error or "Meta did not confirm message acceptance."
    lowered = error.lower()
    if "190" in error or "expired" in lowered or "invalid token" in lowered:
        return "token_expired", "Meta rejected the access token. Reconnect this channel."
    if "permission" in lowered or "(10)" in error or "(200)" in error:
        return "permission_required", "Meta messaging permission is missing or has not been approved."
    if "131047" in error or "window" in lowered:
        return "messaging_window_closed", "The messaging window is closed. WhatsApp requires an approved template."
    if "rate" in lowered or "429" in error or "130429" in error:
        return "rate_limited", "Meta rate-limited the request. Try again later."
    if "timeout" in lowered or "timed out" in lowered or "network" in lowered:
        return "delivery_unconfirmed", "The provider response was not received. Check the channel before resending to avoid duplicates."
    return "provider_rejected", "Meta did not accept this message. Check recipient, permissions and approved template configuration."


def dispatch_message(message_id):
    with transaction.atomic():
        msg = Message.objects.select_for_update(of=("self",)).select_related("conversation__customer", "conversation__organization").get(pk=message_id)
        if msg.delivery_status != "QUEUED":
            return msg
        msg.delivery_status = "SENDING"
        msg.save(update_fields=["delivery_status", "updated_at"])
    config = None
    try:
        payload = msg.attachment_metadata["dispatch"]
        config, identity = validate_send(msg.conversation, payload)
        token = config.get_credential("access_token")
        if msg.conversation.channel == "INSTAGRAM":
            provider = InstagramMessagingProvider(access_token=token, account_id=config.metadata["destination_id"])
        else:
            provider = WhatsAppMessagingProvider(access_token=token, phone_number_id=config.metadata["destination_id"])
        recipient = identity.external_user_id
        if payload.get("template"):
            template = payload["template"]
            result = provider.send_template_message(recipient, template["name"], template["language"], template.get("components", []))
        elif payload.get("media_url"):
            result = provider.send_media_message(recipient, payload["media_url"], payload["media_type"], payload.get("caption"))
        else:
            result = provider.send_text_message(recipient, payload["text"])
        if result.success and result.external_message_id:
            msg.external_message_id = result.external_message_id
            msg.delivery_status = "SENT"
            msg.provider_timestamp = timezone.now()
            config.metadata = {**config.metadata, "last_accepted_at": timezone.now().isoformat(), "error_code": "", "last_error": ""}
            config.save(update_fields=["metadata", "updated_at"])
        else:
            msg.delivery_status = "FAILED"
            msg.error_code, msg.error_message = classify_error(result.error_message)
    except MessagingUnavailable as exc:
        msg.delivery_status = "FAILED"
        detail = exc.detail
        msg.error_code = str(detail.get("code", "configuration_required")) if isinstance(detail, dict) else "configuration_required"
        msg.error_message = str(detail.get("message", detail)) if isinstance(detail, dict) else str(detail)
    except Exception:
        logger.error("Outbound dispatch interrupted; acceptance unconfirmed", extra={"message_id": str(msg.pk)})
        msg.delivery_status = "FAILED"
        msg.error_code = "delivery_unconfirmed"
        msg.error_message = "Message acceptance is unconfirmed. Check channel activity before resending."
    with transaction.atomic():
        msg.save(update_fields=["external_message_id", "delivery_status", "provider_timestamp", "error_code", "error_message", "updated_at"])
        Conversation.objects.filter(pk=msg.conversation_id).update(last_message_at=timezone.now(), last_message_preview=msg.text[:250])
        if config and msg.error_code in ("permission_required", "token_expired"):
            config.metadata = {**config.metadata, "error_code": msg.error_code, "last_error": msg.error_message}
            config.save(update_fields=["metadata", "updated_at"])
        from apps.core.realtime import broadcast_message_updated
        transaction.on_commit(lambda: broadcast_message_updated(msg))
    if msg.external_message_id:
        from .models import MessageReceipt
        from .services import ConversationService
        for receipt in MessageReceipt.objects.filter(organization=msg.conversation.organization, channel=msg.conversation.channel, external_message_id=msg.external_message_id).order_by("created_at"):
            ConversationService.update_message_delivery_status(msg.external_message_id, receipt.status, provider_timestamp=receipt.provider_timestamp, organization=msg.conversation.organization, channel=msg.conversation.channel)
        msg.refresh_from_db()
    return msg
