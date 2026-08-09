"""
Real-time event broadcasting service.
Dispatches typed events to Django Channels WebSocket consumer groups.
Enforces database-first transaction.on_commit() hooks to guarantee zero state divergence
and prevent phantom broadcasts on database rollback.
"""
import logging
from typing import Any, Dict, Optional
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("apps.core.realtime")


class EventTypes:
    """
    Standardized typed real-time event names.
    """
    NEW_LEAD = "NEW_LEAD"
    LEAD_UPDATED = "LEAD_UPDATED"
    NEW_MESSAGE = "NEW_MESSAGE"
    MESSAGE_UPDATED = "MESSAGE_UPDATED"
    CONVERSATION_UPDATED = "CONVERSATION_UPDATED"
    BOOKING_CREATED = "BOOKING_CREATED"
    BOOKING_UPDATED = "BOOKING_UPDATED"
    UNREAD_COUNT_UPDATED = "UNREAD_COUNT_UPDATED"
    DASHBOARD_STATS_UPDATED = "DASHBOARD_STATS_UPDATED"
    MESSAGING_WINDOW_UPDATED = "MESSAGING_WINDOW_UPDATED"


def broadcast_event(group_name: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Dispatches an event to a Django Channels group via the channel layer.
    Safely handles both synchronous threads and active asyncio event loops.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channel layer unavailable; skipped broadcast of %s to %s", event_type, group_name)
        return

    event = {
        "type": "realtime_event",
        "event_type": event_type,
        "payload": payload,
        "timestamp": timezone.now().isoformat(),
    }
    try:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.create_task(channel_layer.group_send(group_name, event))
        else:
            async_to_sync(channel_layer.group_send)(group_name, event)
        logger.debug("Broadcast event %s to group %s successfully", event_type, group_name)
    except Exception as exc:
        logger.error("Failed to broadcast real-time event %s to %s: %s", event_type, group_name, exc)


def broadcast_on_commit(group_name: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Ensures the broadcast executes ONLY after the current database transaction commits.
    If no transaction is active, broadcasts immediately.
    """
    try:
        connection = transaction.get_connection()
        if connection.in_atomic_block:
            transaction.on_commit(lambda: broadcast_event(group_name, event_type, payload))
            return
    except Exception as exc:
        logger.warning("Could not check atomic block state (%s); broadcasting immediately", exc)

    broadcast_event(group_name, event_type, payload)


# ─── Domain Broadcast Helpers ──────────────────────────────────────────────────

def broadcast_new_message(message, conversation=None, lead_id: Optional[str] = None) -> None:
    """
    Broadcasts a newly persisted inbound or outbound message to:
    1. Global admin dashboard
    2. Specific conversation channel
    3. Specific lead channel (if associated)
    """
    conv = conversation or getattr(message, "conversation", None)
    conv_id = str(conv.id) if conv else str(message.conversation_id)

    # Check 24h messaging window status
    is_window_open = True
    window_expires_at = None
    if conv and conv.channel == "INSTAGRAM":
        # Calculate from latest inbound message
        from datetime import timedelta
        from apps.conversations.models import Message
        last_inbound = (
            Message.objects.filter(
                conversation=conv,
                direction=Message.Direction.INBOUND,
            )
            .order_by("-provider_timestamp", "-created_at")
            .first()
        )
        if last_inbound:
            inbound_ts = last_inbound.provider_timestamp or last_inbound.created_at
            expires_at = inbound_ts + timedelta(hours=24)
            is_window_open = timezone.now() < expires_at
            window_expires_at = expires_at.isoformat()
        else:
            is_window_open = False

    # Resolve lead_id if not explicitly provided
    resolved_lead_id = lead_id
    if not resolved_lead_id and conv:
        from apps.leads.models import Lead
        lead = Lead.objects.filter(conversation=conv, is_deleted=False).order_by("-created_at").first()
        if lead:
            resolved_lead_id = str(lead.id)

    payload = {
        "id": str(message.id),
        "conversation_id": conv_id,
        "lead_id": resolved_lead_id,
        "direction": message.direction,
        "text": message.text,
        "message_type": message.message_type,
        "delivery_status": message.delivery_status,
        "provider_timestamp": (
            message.provider_timestamp.isoformat() if message.provider_timestamp else None
        ),
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "is_read": message.is_read,
        "is_window_open": is_window_open,
        "window_expires_at": window_expires_at,
    }

    # Broadcast to admin dashboard
    broadcast_on_commit("admin_dashboard", EventTypes.NEW_MESSAGE, payload)

    # Broadcast to conversation group
    broadcast_on_commit(f"conversation_{conv_id}", EventTypes.NEW_MESSAGE, payload)

    # Broadcast to lead group if exists
    if resolved_lead_id:
        broadcast_on_commit(f"lead_{resolved_lead_id}", EventTypes.NEW_MESSAGE, payload)


def broadcast_message_updated(message, conversation=None, lead_id: Optional[str] = None) -> None:
    """
    Broadcasts message delivery/read status updates.
    """
    conv = conversation or getattr(message, "conversation", None)
    conv_id = str(conv.id) if conv else str(message.conversation_id)

    payload = {
        "id": str(message.id),
        "conversation_id": conv_id,
        "delivery_status": message.delivery_status,
        "is_read": message.is_read,
        "updated_at": message.updated_at.isoformat() if hasattr(message, "updated_at") and message.updated_at else timezone.now().isoformat(),
    }

    broadcast_on_commit("admin_dashboard", EventTypes.MESSAGE_UPDATED, payload)
    broadcast_on_commit(f"conversation_{conv_id}", EventTypes.MESSAGE_UPDATED, payload)
    if lead_id:
        broadcast_on_commit(f"lead_{lead_id}", EventTypes.MESSAGE_UPDATED, payload)


def broadcast_new_lead(lead) -> None:
    """
    Broadcasts newly created sales opportunity lead to admin dashboard.
    """
    customer_name = ""
    if lead.customer:
        customer_name = getattr(lead.customer, "display_name", "") or "New Customer"

    payload = {
        "id": str(lead.id),
        "customer_id": str(lead.customer_id) if lead.customer_id else None,
        "customer_name": customer_name,
        "source_channel": lead.source_channel,
        "status": lead.status,
        "priority": lead.priority,
        "summary": lead.summary,
        "service_name": lead.service.name if lead.service else None,
        "created_at": lead.created_at.isoformat() if lead.created_at else timezone.now().isoformat(),
    }

    broadcast_on_commit("admin_dashboard", EventTypes.NEW_LEAD, payload)
    broadcast_on_commit("admin_dashboard", EventTypes.DASHBOARD_STATS_UPDATED, {})


def broadcast_lead_updated(lead) -> None:
    """
    Broadcasts lead updates (status changes, assignment, notes).
    """
    payload = {
        "id": str(lead.id),
        "status": lead.status,
        "priority": lead.priority,
        "summary": lead.summary,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else timezone.now().isoformat(),
    }

    broadcast_on_commit("admin_dashboard", EventTypes.LEAD_UPDATED, payload)
    broadcast_on_commit(f"lead_{lead.id}", EventTypes.LEAD_UPDATED, payload)
    broadcast_on_commit("admin_dashboard", EventTypes.DASHBOARD_STATS_UPDATED, {})


def broadcast_booking_created(booking) -> None:
    """
    Broadcasts appointment booking confirmation to admin dashboard.
    """
    customer_name = "Customer"
    if booking.customer:
        customer_name = getattr(booking.customer, "display_name", "") or "Customer"

    payload = {
        "id": str(booking.id),
        "status": booking.status,
        "customer_name": customer_name,
        "service_name": booking.service.name if booking.service else "Photography Session",
        "starts_at": booking.starts_at.isoformat() if hasattr(booking, "starts_at") and booking.starts_at else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else timezone.now().isoformat(),
    }

    broadcast_on_commit("admin_dashboard", EventTypes.BOOKING_CREATED, payload)
    broadcast_on_commit("admin_dashboard", EventTypes.DASHBOARD_STATS_UPDATED, {})


def broadcast_booking_updated(booking) -> None:
    """
    Broadcasts appointment booking update/cancellation.
    """
    payload = {
        "id": str(booking.id),
        "status": booking.status,
        "updated_at": booking.updated_at.isoformat() if booking.updated_at else timezone.now().isoformat(),
    }

    broadcast_on_commit("admin_dashboard", EventTypes.BOOKING_UPDATED, payload)
    broadcast_on_commit("admin_dashboard", EventTypes.DASHBOARD_STATS_UPDATED, {})


def broadcast_dashboard_stats_updated() -> None:
    """
    Broadcasts notification that dashboard metrics have updated.
    """
    broadcast_on_commit("admin_dashboard", EventTypes.DASHBOARD_STATS_UPDATED, {})
