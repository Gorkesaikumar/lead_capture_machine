from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Tests for real-time event broadcasting, transaction on_commit guarantees, and pipeline delivery.
"""
from unittest.mock import patch
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from config.asgi import application
from apps.customers.models import Customer
from apps.conversations.models import Conversation, Message
from apps.leads.models import Lead
from apps.services.models import PhotographyService
from apps.core.realtime import (
    EventTypes,
    broadcast_on_commit,
    broadcast_new_message,
    broadcast_new_lead,
)

User = get_user_model()


class RealtimeEventsTests(TransactionTestCase):
    """
    Validates WebSocket real-time delivery and ACID transaction safety.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin_realtime@example.com",
            password="securepassword123",
            full_name="Admin Realtime",
            is_staff=True,
            is_active=True,
        )
        add_member(self.admin)
        self.token, _ = Token.objects.get_or_create(user=self.admin)
        self.customer = Customer.objects.create(organization=test_workspace(),
            display_name="Priya Sharma",
            primary_phone="+919876543210",
        )
        self.service = PhotographyService.objects.create(organization=test_workspace(),
            name="Baby Shoot",
            slug="baby-shoot",
            duration_minutes=60,
            base_price=15000.00,
            is_active=True,
        )

    @database_sync_to_async
    def _create_message_and_broadcast(self):
        conv = Conversation.objects.create(organization=test_workspace(),
            customer=self.customer,
            channel="INSTAGRAM",
        )
        msg = Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            text="Hello, I want to book a baby photoshoot!",
            external_message_id="msg_ws_101",
        )
        broadcast_new_message(msg, conversation=conv)
        return str(msg.id)

    @database_sync_to_async
    def _create_lead_and_broadcast(self):
        lead = create_lead(
            customer=self.customer,
            source_channel="INSTAGRAM",
            service=self.service,
            status=Lead.Status.NEW,
            summary="Inquiry for Baby Shoot",
        )
        broadcast_new_lead(lead)
        return str(lead.id)

    async def test_websocket_receives_new_message_event(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/admin/dashboard/?token={self.token.key}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Discard initial connection established message
        ack = await communicator.receive_json_from()
        self.assertEqual(ack.get("type"), "CONNECTION_ESTABLISHED")

        msg_id = await self._create_message_and_broadcast()

        # Verify client receives NEW_MESSAGE
        event = await communicator.receive_json_from()
        self.assertEqual(event.get("type"), EventTypes.NEW_MESSAGE)
        payload = event.get("payload", {})
        self.assertEqual(payload.get("id"), msg_id)
        self.assertEqual(payload.get("text"), "Hello, I want to book a baby photoshoot!")
        self.assertEqual(payload.get("direction"), "INBOUND")

        await communicator.disconnect()

    async def test_websocket_receives_new_lead_event(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/admin/dashboard/?token={self.token.key}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()  # ACK

        lead_id = await self._create_lead_and_broadcast()

        # Receive NEW_LEAD
        event = await communicator.receive_json_from()
        self.assertEqual(event.get("type"), EventTypes.NEW_LEAD)
        payload = event.get("payload", {})
        self.assertEqual(payload.get("id"), lead_id)
        self.assertEqual(payload.get("status"), "NEW")

        # Also receive DASHBOARD_STATS_UPDATED
        stats_event = await communicator.receive_json_from()
        self.assertEqual(stats_event.get("type"), EventTypes.DASHBOARD_STATS_UPDATED)

        await communicator.disconnect()

    def test_transaction_rollback_prevents_broadcast(self):
        """
        Ensures transaction.on_commit handlers are cancelled when an atomic transaction rolls back.
        """
        with patch("apps.core.realtime.broadcast_event") as mock_broadcast:
            try:
                with transaction.atomic():
                    broadcast_on_commit("admin_dashboard", "TEST_EVENT", {"data": "test"})
                    # Force rollback
                    raise ValueError("Simulated failure")
            except ValueError:
                pass

            # Mock should NOT have been called because transaction rolled back
            mock_broadcast.assert_not_called()

    @database_sync_to_async
    def _other_workspace_message(self):
        owner = User.objects.create_user(email="other-ws@example.test", password="Secret!789")
        org = make_organization(name="Other", owner=owner)
        customer = Customer.objects.create(organization=org, display_name="Private customer")
        conv = Conversation.objects.create(organization=org, customer=customer, channel="INSTAGRAM")
        msg = Message.objects.create(conversation=conv, direction="INBOUND", text="Private message")
        broadcast_new_message(msg)
        return str(conv.pk)

    async def test_other_workspace_events_and_conversation_are_denied(self):
        communicator = WebsocketCommunicator(application, "/ws/admin/dashboard/", subprotocols=["v4", f"token.{self.token.key}"])
        connected, protocol = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual(protocol, "v4")
        await communicator.receive_json_from()
        other_id = await self._other_workspace_message()
        self.assertTrue(await communicator.receive_nothing(timeout=0.1))
        denied = WebsocketCommunicator(application, f"/ws/admin/conversations/{other_id}/", subprotocols=["v4", f"token.{self.token.key}"])
        connected, _ = await denied.connect()
        self.assertFalse(connected)
        await denied.disconnect()
        await communicator.disconnect()

    async def test_revoked_token_closes_existing_connection(self):
        communicator = WebsocketCommunicator(application, "/ws/admin/dashboard/", subprotocols=["v4", f"token.{self.token.key}"])
        self.assertTrue((await communicator.connect())[0])
        await communicator.receive_json_from()
        await database_sync_to_async(Token.objects.filter(user=self.admin).delete)()
        await self._create_message_and_broadcast()
        event = await communicator.receive_output()
        self.assertEqual(event["type"], "websocket.close")
        await communicator.disconnect()
