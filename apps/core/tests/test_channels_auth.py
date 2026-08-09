"""
Tests for Django Channels WebSocket authentication and consumer behavior.
"""
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from config.asgi import application

User = get_user_model()


class ChannelsAuthTests(TransactionTestCase):
    """
    Tests WebSocket token authentication middleware and consumer authorization.
    """

    def setUp(self):
        # Create Admin user
        self.admin_user = User.objects.create_user(
            email="admin_ws@example.com",
            password="securepassword123",
            full_name="Admin User",
            is_staff=True,
            is_active=True,
        )
        self.admin_token, _ = Token.objects.get_or_create(user=self.admin_user)

        # Create Normal (Non-staff) user
        self.regular_user = User.objects.create_user(
            email="regular_ws@example.com",
            password="securepassword123",
            full_name="Regular User",
            is_staff=False,
            is_active=True,
        )
        self.regular_token, _ = Token.objects.get_or_create(user=self.regular_user)

    async def test_admin_token_can_connect_and_receives_ack(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/admin/dashboard/?token={self.admin_token.key}",
        )
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Expect initial connection established message
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "CONNECTION_ESTABLISHED")
        self.assertEqual(response.get("user"), self.admin_user.email)

        # Test heartbeat ping/pong
        await communicator.send_json_to({"type": "PING"})
        pong_response = await communicator.receive_json_from()
        self.assertEqual(pong_response.get("type"), "PONG")

        await communicator.disconnect()

    async def test_anonymous_connection_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/admin/dashboard/",
        )
        connected, subprotocol = await communicator.connect()
        # Non-authenticated connection must not connect
        self.assertFalse(connected)

    async def test_invalid_token_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/admin/dashboard/?token=invalid_fake_token_key_12345",
        )
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)

    async def test_non_staff_token_is_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/admin/dashboard/?token={self.regular_token.key}",
        )
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
