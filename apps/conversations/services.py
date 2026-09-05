"""
Conversation and normalized message storage service.
Guarantees message idempotency, handles concurrent webhook delivery, and updates conversation state.
"""
import logging
from typing import Any, Dict, Optional, Tuple
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.conversations.models import Conversation, Message
from apps.customers.services import CustomerResolutionService
from apps.core.logging import PipelineLogger, PipelineStage

logger = logging.getLogger("apps.conversations")


class ConversationService:
    """
    Business service for storing inbound/outbound normalized messages and managing conversation state.
    """

    @classmethod
    def store_inbound_message(
        cls,
        normalized_data: Dict[str, Any],
        organization: "Organization",
        plog: Optional[PipelineLogger] = None,
    ) -> Tuple[Message, bool]:
        """
        Stores an incoming normalized message from Instagram or WhatsApp webhook.

        Workflow:
        1. Validates input and checks message idempotency (fast-path).
        2. Resolves or creates the Customer.
        3. Atomically resolves/creates Conversation, persists Message, and updates conversation state.
        4. Recovers safely from concurrent duplicate webhook deliveries.

        Returns:
            Tuple[Message, bool]: (Message instance, created boolean)
        """
        channel = str(normalized_data.get("channel", "")).upper().strip()
        external_user_id = str(normalized_data.get("external_user_id", "")).strip()
        external_message_id = str(normalized_data.get("external_message_id", "")).strip()

        if not organization or channel not in ("INSTAGRAM", "WHATSAPP") or not external_user_id or not external_message_id:
            raise ValueError("Channel and external_user_id are required to store an inbound message.")

        # 1. Fast-path Idempotency Check: deduplicate existing external message ID
        if external_message_id:
            existing_msg = (
                Message.objects.select_related("conversation", "conversation__customer")
                .filter(external_message_id=external_message_id, conversation__organization=organization, conversation__channel=channel)
                .first()
            )
            if existing_msg:
                _log = plog or PipelineLogger(base_logger=logger)
                _log.info(
                    PipelineStage.MESSAGE_SAVED,
                    "Duplicate inbound message ignored (idempotency)",
                    external_message_id=external_message_id,
                    is_duplicate=True,
                )
                return existing_msg, False

        # Parse provider timestamp
        raw_timestamp = normalized_data.get("provider_timestamp")
        if isinstance(raw_timestamp, str):
            provider_timestamp = parse_datetime(raw_timestamp) or timezone.now()
        elif raw_timestamp:
            provider_timestamp = raw_timestamp
        else:
            provider_timestamp = timezone.now()

        text = normalized_data.get("text", "") or ""
        message_type = normalized_data.get("message_type", Message.MessageType.TEXT)
        attachment_metadata = normalized_data.get("attachment_metadata", {}) or {}
        raw_payload = normalized_data.get("raw_payload", {}) or {}
        display_name = normalized_data.get("display_name")
        phone_number = normalized_data.get("phone_number")
        username = normalized_data.get("username")
        external_thread_id = normalized_data.get("external_thread_id", "") or ""

        # 2. Resolve or create Customer
        customer, customer_created = CustomerResolutionService.resolve_customer(
            channel=channel,
            external_user_id=external_user_id,
            organization=organization,
            metadata=raw_payload,
            display_name=display_name,
            phone_number=phone_number,
            username=username,
        )
        _log = plog or PipelineLogger(base_logger=logger)
        _log.set(customer_id=str(customer.id))
        _log.info(
            PipelineStage.CUSTOMER_RESOLVED,
            "Customer resolved",
            customer_id=str(customer.id),
            channel=channel,
            is_new_customer=customer_created,
        )

        # 3. Atomically persist Conversation and Message with race-condition handling
        try:
            with transaction.atomic():
                # Get or create Conversation for this customer on this channel
                conversation, conv_created = Conversation.objects.get_or_create(
                    customer=customer,
                    channel=channel,
                    defaults={
                        "organization": organization,
                        "external_thread_id": external_thread_id,
                        "last_message_at": provider_timestamp,
                        "last_message_preview": (text or f"[{message_type}]")[:250],
                        "unread_count": 0,
                    },
                )
                _log.set(conversation_id=str(conversation.id))
                _log.info(
                    PipelineStage.CONVERSATION_RESOLVED,
                    "Conversation resolved",
                    conversation_id=str(conversation.id),
                    is_new_conversation=conv_created,
                )

                conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)

                # Persist message (default is_read=False for new inbound messages)
                message = Message.objects.create(
                    conversation=conversation,
                    direction=Message.Direction.INBOUND,
                    external_message_id=external_message_id,
                    message_type=message_type,
                    text=text,
                    attachment_metadata=attachment_metadata,
                    provider_timestamp=provider_timestamp,
                    delivery_status=Message.DeliveryStatus.DELIVERED,
                    raw_payload=raw_payload,
                    is_read=False,
                )

                # Derive the true unread count from persisted messages in the database
                unread_count = Message.objects.filter(
                    conversation=conversation,
                    direction=Message.Direction.INBOUND,
                    is_read=False,
                ).count()

                # Update conversation state
                preview = (text or f"[{message_type}]")[:250]
                is_latest = not conversation.last_message_at or provider_timestamp >= conversation.last_message_at
                Conversation.objects.filter(id=conversation.id).update(
                    last_message_at=provider_timestamp if is_latest else conversation.last_message_at,
                    last_message_preview=preview if is_latest else conversation.last_message_preview,
                    unread_count=unread_count,
                    status=Conversation.Status.ACTIVE,
                    updated_at=timezone.now(),
                )
                conversation.refresh_from_db()

                _log.info(
                    PipelineStage.MESSAGE_SAVED,
                    "Inbound message stored",
                    message_id=str(message.id),
                    external_message_id=external_message_id,
                    conversation_id=str(conversation.id),
                    customer_id=str(customer.id),
                    message_type=message_type,
                    is_duplicate=False,
                )
                return message, True

        except IntegrityError:
            # 4. Handle concurrent duplicate webhook delivery
            if external_message_id:
                _log.warning(
                    PipelineStage.MESSAGE_SAVED,
                    "Concurrent duplicate message insertion — recovering existing record",
                    external_message_id=external_message_id,
                    is_duplicate=True,
                )
                recovered_msg = (
                    Message.objects.select_related("conversation", "conversation__customer")
                    .filter(external_message_id=external_message_id, conversation__organization=organization, conversation__channel=channel)
                    .first()
                )
                if recovered_msg:
                    return recovered_msg, False

            raise

    @classmethod
    def store_outbound_message(
        cls,
        conversation: Conversation,
        text: str,
        external_message_id: Optional[str] = None,
        message_type: str = Message.MessageType.TEXT,
        attachment_metadata: Optional[Dict[str, Any]] = None,
        provider_timestamp: Optional[Any] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Stores an outbound message sent by the Studio Admin to a customer.
        Updates conversation last_message_at without incrementing unread_count.
        """
        now = provider_timestamp or timezone.now()
        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                direction=Message.Direction.OUTBOUND,
                external_message_id=external_message_id or "",
                message_type=message_type,
                text=text or "",
                attachment_metadata=attachment_metadata or {},
                provider_timestamp=now,
                delivery_status=Message.DeliveryStatus.SENT,
                raw_payload=raw_payload or {},
            )

            preview = (text or f"[{message_type}]")[:250]
            Conversation.objects.filter(id=conversation.id).update(
                last_message_at=now,
                last_message_preview=preview,
                updated_at=timezone.now(),
            )

            return message

    @classmethod
    def update_message_delivery_status(
        cls,
        external_message_id: str,
        delivery_status: str,
        error_details: Optional[Dict[str, Any]] = None,
        provider_timestamp: Optional[Any] = None,
        organization=None,
        channel=None,
    ) -> Optional[Message]:
        """
        Updates delivery status (SENT, DELIVERED, READ, FAILED) for a message identified by external_message_id.
        """
        if not external_message_id:
            return None

        status_mapping = {
            "sent": Message.DeliveryStatus.SENT,
            "delivered": Message.DeliveryStatus.DELIVERED,
            "read": Message.DeliveryStatus.READ,
            "failed": Message.DeliveryStatus.FAILED,
            "SENT": Message.DeliveryStatus.SENT,
            "DELIVERED": Message.DeliveryStatus.DELIVERED,
            "READ": Message.DeliveryStatus.READ,
            "FAILED": Message.DeliveryStatus.FAILED,
        }
        target_status = status_mapping.get(delivery_status)
        if not target_status or organization is None or channel is None:
            return None

        from .models import MessageReceipt
        MessageReceipt.objects.get_or_create(organization=organization, channel=channel, external_message_id=external_message_id, status=target_status, defaults={"provider_timestamp": provider_timestamp})

        with transaction.atomic():
            message = (
                Message.objects.select_for_update(of=("self",))
                .filter(external_message_id=external_message_id, conversation__organization=organization, conversation__channel=channel, direction="OUTBOUND")
                .first()
            )
            if not message:
                logger.warning("Message with external_message_id=%s not found for status update", external_message_id)
                return None

            rank = {"PENDING": 0, "QUEUED": 0, "SENDING": 1, "SENT": 2, "DELIVERED": 3, "READ": 4, "FAILED": -1}
            if message.delivery_status in ("DELIVERED", "READ") and target_status == "FAILED":
                return message
            if target_status != "FAILED" and rank.get(target_status, 0) <= rank.get(message.delivery_status, 0):
                return message
            message.delivery_status = target_status
            update_fields = ["delivery_status", "updated_at"]

            if error_details:
                meta = message.attachment_metadata or {}
                meta["delivery_error"] = error_details
                message.attachment_metadata = meta
                update_fields.append("attachment_metadata")

            message.save(update_fields=update_fields)
            logger.info(
                "Updated message id=%s (wamid=%s) delivery status to %s",
                message.id,
                external_message_id,
                target_status,
            )

        # Synchronize status on Notification records if present
        try:
            from apps.notifications.services import NotificationService
            NotificationService.update_status_by_external_id(
                external_message_id=external_message_id,
                delivery_status=delivery_status,
                error_details=error_details,
                provider_timestamp=provider_timestamp,
                organization=organization,
                channel=channel,
            )
        except Exception as notif_exc:
            logger.warning("Failed to sync notification status for %s: %s", external_message_id, str(notif_exc))

        return message

    @classmethod
    def is_within_24h_window(cls, channel: str, external_user_id: str, organization=None) -> bool:
        """
        Determines whether the 24-hour WhatsApp customer service window is open.
        Returns True if customer sent an inbound message within the last 24 hours.
        """
        if organization is None:
            return False
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)

        last_inbound = (
            Message.objects.filter(
                conversation__organization=organization,
                conversation__channel=channel,
                conversation__customer__identities__channel=channel,
                conversation__customer__identities__external_user_id=external_user_id,
                direction=Message.Direction.INBOUND,
            )
            .order_by("-provider_timestamp", "-created_at")
            .first()
        )
        if not last_inbound:
            return False

        msg_time = last_inbound.provider_timestamp or last_inbound.created_at
        return cutoff < msg_time <= timezone.now()

    @classmethod
    def mark_conversation_as_read(cls, conversation: Conversation) -> Conversation:
        """
        Resets unread counter for a conversation when reviewed by Admin.
        """
        conversation.mark_read()
        logger.info("Marked conversation id=%s as read", conversation.id)
        return conversation
