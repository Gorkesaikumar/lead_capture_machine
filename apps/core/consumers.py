"""
Django Channels WebSocket consumers for real-time admin events.
Handles connection lifecycles, authentication verification, channel group management,
heartbeat/ping-pong, and structured JSON event delivery.
"""
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger("apps.core.consumers")


class BaseAdminConsumer(AsyncJsonWebsocketConsumer):
    """
    Base consumer providing common authentication, heartbeat, and dispatch logic.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not (user.is_staff or user.is_superuser):
            logger.warning(
                "WebSocket connection REJECTED (Unauthorized): user=%s path=%s client=%s",
                user,
                self.scope.get("path"),
                self.scope.get("client"),
            )
            # Close with custom 4403 (Forbidden) code
            await self.close(code=4403)
            return

        self.groups_joined = []
        await self.setup_groups()
        for group in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()
        logger.info(
            "WebSocket CONNECTED: user=%s channel=%s groups=%s client=%s",
            user.email if hasattr(user, "email") else user,
            self.channel_name,
            self.groups_joined,
            self.scope.get("client"),
        )

        # Send connection acknowledgment
        await self.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "user": getattr(user, "email", str(user)),
            "timestamp": timezone.now().isoformat(),
        })

    async def disconnect(self, close_code):
        if hasattr(self, "groups_joined"):
            for group in self.groups_joined:
                await self.channel_layer.group_discard(group, self.channel_name)
        logger.info(
            "WebSocket DISCONNECTED: user=%s channel=%s code=%s groups=%s",
            self.scope.get("user"),
            self.channel_name,
            close_code,
            getattr(self, "groups_joined", []),
        )

    async def receive_json(self, content, **kwargs):
        """
        Handle incoming client messages such as ping heartbeats.
        """
        msg_type = content.get("type", "").upper()
        if msg_type == "PING":
            await self.send_json({
                "type": "PONG",
                "timestamp": timezone.now().isoformat(),
            })

    async def realtime_event(self, event):
        """
        Handler for channel layer group messages.
        Dispatches typed events to the connected client.
        """
        await self.send_json({
            "type": event.get("event_type", "UNKNOWN_EVENT"),
            "payload": event.get("payload", {}),
            "timestamp": event.get("timestamp", timezone.now().isoformat()),
        })

    async def setup_groups(self):
        """Override in subclasses to specify groups to join."""
        raise NotImplementedError


class AdminDashboardConsumer(BaseAdminConsumer):
    """
    Consumer for global admin dashboard updates (new leads, stats, bookings, notifications).
    Route: /ws/admin/dashboard/ or /ws/dashboard/
    """

    async def setup_groups(self):
        self.groups_joined.append("admin_dashboard")


class ConversationConsumer(BaseAdminConsumer):
    """
    Consumer for conversation message stream and window status.
    Route: /ws/conversations/<conversation_id>/ or /ws/admin/conversations/<conversation_id>/
    """

    async def setup_groups(self):
        conversation_id = self.scope.get("url_route", {}).get("kwargs", {}).get("conversation_id")
        if conversation_id:
            self.groups_joined.append(f"conversation_{conversation_id}")
        # Also join global dashboard so unified stream receives updates
        self.groups_joined.append("admin_dashboard")


class LeadConsumer(BaseAdminConsumer):
    """
    Consumer for single lead conversation and activity stream.
    Route: /ws/leads/<lead_id>/ or /ws/admin/leads/<lead_id>/
    """

    async def setup_groups(self):
        lead_id = self.scope.get("url_route", {}).get("kwargs", {}).get("lead_id")
        if lead_id:
            self.groups_joined.append(f"lead_{lead_id}")
        self.groups_joined.append("admin_dashboard")
