"""
Notification Service & Orchestrator.
Coordinates outbound customer notifications across Instagram and WhatsApp without coupling
domain modules directly to Meta Graph APIs.
"""
import logging
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.audit.services import AuditService
from apps.conversations.models import Conversation
from apps.conversations.services import ConversationService
from apps.customers.models import Customer, CustomerIdentity
from apps.integrations.meta.base import OutboundResult
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.notifications.formatters import NotificationFormatter
from apps.notifications.models import Notification

logger = logging.getLogger("apps.notifications")


class PermanentNotificationError(Exception):
    """Raised when an unrecoverable provider or recipient error occurs."""
    pass


class TransientNotificationError(Exception):
    """Raised when a temporary network or provider error occurs, eligible for retry."""
    pass


class NotificationService:
    """
    Unified entry point for dispatching customer notifications.
    """

    @classmethod
    def send_notification(
        cls,
        customer: Customer,
        channel: str,
        notification_type: str,
        context: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Tuple[Notification, bool]:
        """
        Creates and schedules a Notification for delivery.

        Returns:
            Tuple[Notification, bool]: (notification instance, is_new boolean)
        """
        ctx = context or {}
        # Pre-populate customer name if omitted
        if "customer_name" not in ctx and customer.display_name:
            ctx["customer_name"] = customer.display_name

        rendered_text = NotificationFormatter.format(
            notification_type=notification_type,
            context=ctx,
            channel=channel,
        )

        # 1. Check idempotency
        if idempotency_key:
            existing = Notification.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                logger.info(
                    "Idempotent notification hit for key=%s (status=%s, id=%s)",
                    idempotency_key,
                    existing.status,
                    existing.id,
                )
                return existing, False

        # 2. Create Notification record
        try:
            with transaction.atomic():
                notification = Notification.objects.create(
                    customer=customer,
                    channel=channel,
                    notification_type=notification_type,
                    status=Notification.Status.PENDING,
                    idempotency_key=idempotency_key,
                    context=ctx,
                    rendered_text=rendered_text,
                )
        except IntegrityError:
            # Concurrent duplicate idempotency key insertion
            existing = Notification.objects.filter(idempotency_key=idempotency_key).first()
            return existing, False

        # 3. Dispatch asynchronously via Celery or synchronously in eager mode
        from apps.notifications.tasks import dispatch_notification_task

        is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
        if not async_delivery or is_eager:
            cls.dispatch_now(str(notification.id))
            notification.refresh_from_db()
        else:
            try:
                dispatch_notification_task.delay(str(notification.id))
            except Exception as exc:
                logger.warning("Celery dispatch unavailable (%s), falling back to synchronous execution", str(exc))
                cls.dispatch_now(str(notification.id))
                notification.refresh_from_db()

        return notification, True

    # -------------------------------------------------------------------------
    # High-level domain notification helpers
    # -------------------------------------------------------------------------

    @classmethod
    def send_booking_link(
        cls,
        customer: Customer,
        booking_url: str,
        channel: Optional[str] = None,
        service_name: Optional[str] = None,
        lead_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Tuple[Notification, bool]:
        """
        Sends a private booking link invitation.
        """
        target_channel = channel or cls._detect_best_channel(customer)
        key = idempotency_key or (f"booking_link_{lead_id}" if lead_id else None)
        context = {
            "booking_url": booking_url,
            "service_name": service_name or "Photo Shoot",
            "customer_name": customer.display_name,
        }
        notif, is_new = cls.send_notification(
            customer=customer,
            channel=target_channel,
            notification_type=Notification.NotificationType.BOOKING_LINK,
            context=context,
            idempotency_key=key,
            async_delivery=async_delivery,
        )
        if is_new:
            AuditService.record_booking_link_sent(notif)
        return notif, is_new

    @classmethod
    def send_booking_confirmation(
        cls,
        booking: Any,
        channel: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Tuple[Notification, bool]:
        """
        Sends a booking confirmation upon successful reservation.
        """
        target_channel = channel or cls._detect_best_channel(booking.customer)
        key = idempotency_key or f"booking_confirm_{booking.id}"
        context = {
            "customer_name": booking.customer.display_name,
            "service_name": booking.service.name if booking.service else "Photo Session",
            "start_time": booking.starts_at.strftime("%A, %B %d, %Y at %I:%M %p") if booking.starts_at else "",
            "duration_minutes": booking.service.duration_minutes if booking.service else 60,
            "studio_address": "Photo Studio Main Branch",
        }
        return cls.send_notification(
            customer=booking.customer,
            channel=target_channel,
            notification_type=Notification.NotificationType.BOOKING_CONFIRMATION,
            context=context,
            idempotency_key=key,
            async_delivery=async_delivery,
        )

    @classmethod
    def send_booking_reminder(
        cls,
        booking: Any,
        channel: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Tuple[Notification, bool]:
        """
        Sends a 24-hour reminder before a scheduled session.
        """
        target_channel = channel or cls._detect_best_channel(booking.customer)
        key = idempotency_key or f"booking_reminder_{booking.id}_{booking.starts_at.date()}"
        context = {
            "customer_name": booking.customer.display_name,
            "service_name": booking.service.name if booking.service else "Photo Session",
            "start_time": booking.starts_at.strftime("%A, %B %d at %I:%M %p") if booking.starts_at else "",
            "studio_address": "Photo Studio Main Branch",
        }
        return cls.send_notification(
            customer=booking.customer,
            channel=target_channel,
            notification_type=Notification.NotificationType.BOOKING_REMINDER,
            context=context,
            idempotency_key=key,
            async_delivery=async_delivery,
        )

    @classmethod
    def send_booking_cancellation(
        cls,
        booking: Any,
        channel: Optional[str] = None,
        reason: Optional[str] = None,
        reschedule_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        async_delivery: bool = True,
    ) -> Tuple[Notification, bool]:
        """
        Sends a cancellation notice to the customer.
        """
        target_channel = channel or cls._detect_best_channel(booking.customer)
        key = idempotency_key or f"booking_cancel_{booking.id}"
        context = {
            "customer_name": booking.customer.display_name,
            "service_name": booking.service.name if booking.service else "Photo Session",
            "start_time": booking.starts_at.strftime("%A, %B %d, %Y at %I:%M %p") if booking.starts_at else "",
            "cancellation_reason": reason or "Client or Studio schedule adjustment",
            "booking_url": reschedule_url or "",
        }
        return cls.send_notification(
            customer=booking.customer,
            channel=target_channel,
            notification_type=Notification.NotificationType.BOOKING_CANCELLATION,
            context=context,
            idempotency_key=key,
            async_delivery=async_delivery,
        )

    # -------------------------------------------------------------------------
    # Outbound Dispatch Engine
    # -------------------------------------------------------------------------

    @classmethod
    def dispatch_now(cls, notification_id: str) -> Notification:
        """
        Executes actual outbound dispatch against the appropriate Meta provider.
        Catches errors and classifies them as transient vs permanent.
        """
        with transaction.atomic():
            try:
                notification = Notification.objects.select_for_update(of=("self",)).get(id=notification_id)
            except Notification.DoesNotExist:
                logger.error("Notification %s does not exist for dispatch", notification_id)
                raise PermanentNotificationError(f"Notification {notification_id} not found")

            # Skip if already delivered or sent
            if notification.status in [
                Notification.Status.SENT,
                Notification.Status.DELIVERED,
                Notification.Status.READ,
            ]:
                logger.info("Notification %s already in state %s. Skipping dispatch.", notification_id, notification.status)
                return notification

            if notification.is_permanent_error:
                logger.info("Notification %s has permanent error flag set. Skipping.", notification_id)
                return notification

            # Resolve recipient external user ID
            identity = (
                CustomerIdentity.objects.filter(
                    customer=notification.customer,
                    channel=notification.channel,
                )
                .order_by("-updated_at")
                .first()
            )
            if not identity or not identity.external_user_id:
                err = f"No {notification.channel} identity found for customer {notification.customer.id}"
                logger.error(err)
                notification.mark_failed(err, is_permanent=True)
                return notification

            recipient_id = identity.external_user_id
            ctx = notification.context or {}
            customer_name = ctx.get("customer_name") or notification.customer.display_name
            service_name = ctx.get("service_name")
            booking_url = ctx.get("booking_url")

            logger.info(
                "Dispatching Notification id=%s [%s:%s] to recipient=%s",
                notification.id,
                notification.channel,
                notification.notification_type,
                recipient_id,
            )

            # Route to correct provider
            if notification.channel == Notification.Channel.INSTAGRAM:
                provider = InstagramMessagingProvider()
                if notification.notification_type == Notification.NotificationType.BOOKING_LINK and booking_url:
                    result = provider.send_booking_link_message(
                        recipient_id=recipient_id,
                        booking_url=booking_url,
                        customer_name=customer_name,
                        service_name=service_name,
                    )
                else:
                    result = provider.send_text_message(
                        recipient_id=recipient_id,
                        text=notification.rendered_text,
                    )

            elif notification.channel == Notification.Channel.WHATSAPP:
                provider = WhatsAppMessagingProvider()
                if notification.notification_type == Notification.NotificationType.BOOKING_LINK and booking_url:
                    result = provider.send_booking_link_message(
                        recipient_id=recipient_id,
                        booking_url=booking_url,
                        customer_name=customer_name,
                        service_name=service_name,
                    )
                else:
                    # If within 24h window send rendered text; otherwise send template or text
                    result = provider.send_text_message(
                        recipient_id=recipient_id,
                        text=notification.rendered_text,
                    )
            else:
                err = f"Unsupported delivery channel: {notification.channel}"
                notification.mark_failed(err, is_permanent=True)
                return notification

            # Handle provider outcome
            if result.success:
                ext_msg_id = result.external_message_id or ""
                notification.mark_sent(external_message_id=ext_msg_id)

                # Store outbound message in conversation history
                try:
                    conv, _ = Conversation.objects.get_or_create(
                        customer=notification.customer,
                        channel=notification.channel,
                    )
                    ConversationService.store_outbound_message(
                        conversation=conv,
                        text=notification.rendered_text,
                        external_message_id=ext_msg_id,
                        raw_payload=result.provider_response,
                    )
                except Exception as conv_exc:
                    logger.warning("Failed to append message to conversation history: %s", str(conv_exc))

                logger.info("Notification %s successfully sent (wamid/mid=%s)", notification.id, ext_msg_id)
                return notification

            # Failed dispatch handling
            error_str = result.error_message or "Unknown provider send failure"
            is_perm = cls._is_permanent_error(error_str)

            notification.retry_count += 1
            notification.mark_failed(error_message=error_str, is_permanent=is_perm)

            logger.error(
                "Notification %s dispatch failed (permanent=%s): %s",
                notification.id,
                is_perm,
                error_str,
            )

        if is_perm:
            raise PermanentNotificationError(error_str)
        else:
            raise TransientNotificationError(error_str)


    # -------------------------------------------------------------------------
    # Status Synchronization from Webhooks
    # -------------------------------------------------------------------------

    @classmethod
    def update_status_by_external_id(
        cls,
        external_message_id: str,
        delivery_status: str,
        error_details: Optional[Dict[str, Any]] = None,
        provider_timestamp: Optional[Any] = None,
    ) -> Optional[Notification]:
        """
        Synchronizes delivery status on Notification records matching the external message ID.
        """
        if not external_message_id:
            return None

        status_lower = delivery_status.lower()
        now = provider_timestamp or timezone.now()

        notifications = Notification.objects.filter(external_message_id=external_message_id)
        if not notifications.exists():
            return None

        for notif in notifications:
            if status_lower == "delivered":
                notif.mark_delivered(delivered_at=now)
            elif status_lower == "read":
                notif.mark_read(read_at=now)
            elif status_lower == "failed":
                err_msg = json_err if (json_err := str(error_details)) else "Provider delivery failed"
                notif.mark_failed(error_message=err_msg, is_permanent=True)

        return notifications.first()

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _detect_best_channel(cls, customer: Customer) -> str:
        """
        Auto-detects the best channel for a customer based on their most recently active identity.
        Defaults to WHATSAPP if available, else INSTAGRAM.
        """
        identities = customer.identities.all().order_by("-updated_at")
        if identities.filter(channel=CustomerIdentity.Channel.WHATSAPP).exists():
            return CustomerIdentity.Channel.WHATSAPP
        if identities.filter(channel=CustomerIdentity.Channel.INSTAGRAM).exists():
            return CustomerIdentity.Channel.INSTAGRAM
        return CustomerIdentity.Channel.WHATSAPP

    @classmethod
    def _is_permanent_error(cls, error_message: str) -> bool:
        """
        Classifies whether an error is permanent (do not retry) vs transient (retry).
        """
        permanent_keywords = [
            "invalid parameter",
            "invalid phone",
            "not found",
            "permission",
            "opt-out",
            "unsupported",
            "invalid oauth",
            "bad request",
            "131026",  # WhatsApp: Message undeliverable / out of service
            "131051",  # WhatsApp: User has not opted in / policy
            "100",     # Meta: Invalid parameter
            "190",     # Meta: Access token invalid/expired
            "200",     # Meta: Permission error
        ]
        err_lower = error_message.lower()
        return any(keyword in err_lower for keyword in permanent_keywords)
