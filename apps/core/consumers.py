"""
Django Channels WebSocket consumers for real-time admin events.
Handles connection lifecycles, authentication verification, channel group management,
heartbeat/ping-pong, and structured JSON event delivery.
"""
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone
from channels.db import database_sync_to_async
from urllib.parse import parse_qs


@database_sync_to_async
def resolve_workspace(scope):
    from apps.organizations.models import OrganizationMembership
    from apps.conversations.models import Conversation
    from apps.leads.models import Lead
    from uuid import UUID
    user = scope.get("user")
    if not user or not user.is_authenticated or not user.is_active:
        return None
    from rest_framework.authtoken.models import Token
    if not Token.objects.filter(key=scope.get("auth_token_key"), user=user, user__is_active=True).exists():
        return None
    memberships = OrganizationMembership.objects.filter(user=user, user__is_active=True, is_active=True, organization__is_active=True, organization__is_deleted=False)
    org_id = parse_qs(scope.get("query_string", b"").decode()).get("organization_id", [None])[0]
    if org_id:
        try:
            memberships = memberships.filter(organization_id=UUID(org_id))
        except ValueError:
            return None
    membership = memberships.first()
    if not membership:
        return None
    kwargs = scope.get("url_route", {}).get("kwargs", {})
    for key, model in (("conversation_id", Conversation), ("lead_id", Lead)):
        if key in kwargs:
            try:
                entity_id = UUID(kwargs[key])
            except (ValueError, TypeError):
                return None
            if not model.objects.filter(pk=entity_id, organization=membership.organization, is_deleted=False).exists():
                return None
    return str(membership.organization_id)


logger = logging.getLogger("apps.core.consumers")


class BaseAdminConsumer(AsyncJsonWebsocketConsumer):
    """
    Base consumer providing common authentication, heartbeat, and dispatch logic.
    """

    async def connect(self):
        user = self.scope.get("user")
        self.organization_id = await resolve_workspace(self.scope)
        if not self.organization_id:
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

        await self.accept(subprotocol="v4" if "v4" in self.scope.get("subprotocols", []) else None)
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
        if await resolve_workspace(self.scope) != self.organization_id:
            await self.close(code=4403)
            return
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
        self.groups_joined.append(f"organization_{self.organization_id}")


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
        self.groups_joined.append(f"organization_{self.organization_id}")


class LeadConsumer(BaseAdminConsumer):
    """
    Consumer for single lead conversation and activity stream.
    Route: /ws/leads/<lead_id>/ or /ws/admin/leads/<lead_id>/
    """

    async def setup_groups(self):
        lead_id = self.scope.get("url_route", {}).get("kwargs", {}).get("lead_id")
        if lead_id:
            self.groups_joined.append(f"lead_{lead_id}")
        self.groups_joined.append(f"organization_{self.organization_id}")
