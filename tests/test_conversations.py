"""
Tests for Conversations and Messages domain models, ConversationService idempotency/concurrency, and APIs.
"""
import concurrent.futures
import uuid
import pytest
from django.db import IntegrityError, close_old_connections
from django.utils import timezone
from rest_framework import status
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
from apps.customers.models import Customer


@pytest.mark.django_db(transaction=True)
class TestConversationModelsAndServices:
    def test_conversation_customer_channel_unique_constraint(self):
        """Database enforces unique constraint on (customer, channel)."""
        customer = Customer.objects.create(display_name="Rohan Mehra")
        Conversation.objects.create(
            customer=customer,
            channel=Conversation.Channel.INSTAGRAM,
        )

        with pytest.raises(IntegrityError):
            Conversation.objects.create(
                customer=customer,
                channel=Conversation.Channel.INSTAGRAM,
            )

    def test_message_unique_external_message_id(self):
        """Database enforces unique constraint on external_message_id."""
        customer = Customer.objects.create(display_name="Deepika Roy")
        conv = Conversation.objects.create(
            customer=customer,
            channel=Conversation.Channel.WHATSAPP,
        )

        Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            external_message_id="wamid.123456789",
            text="Hi there",
        )

        with pytest.raises(IntegrityError):
            Message.objects.create(
                conversation=conv,
                direction=Message.Direction.INBOUND,
                external_message_id="wamid.123456789",
                text="Duplicate send",
            )

    def test_store_inbound_message_creates_hierarchy(self):
        """Storing an inbound message resolves customer, creates conversation and message, and increments unread count."""
        msg, created = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_cust_001",
            "external_message_id": "ig_mid_1001",
            "text": "Hello, I would like to check prices for newborn photography",
            "username": "priya_art",
            "display_name": "Priya Arts",
        })

        assert created is True
        assert msg.direction == Message.Direction.INBOUND
        assert msg.text == "Hello, I would like to check prices for newborn photography"
        assert msg.conversation.unread_count == 1
        assert msg.conversation.last_message_at is not None
        assert "Hello, I would like" in msg.conversation.last_message_preview
        assert msg.conversation.customer.display_name == "Priya Arts"

    def test_store_inbound_message_idempotency(self):
        """Re-submitting the same external_message_id returns the existing message without incrementing unread count."""
        payload = {
            "channel": "WHATSAPP",
            "external_user_id": "919999888877",
            "external_message_id": "wamid.idempotent.001",
            "text": "I want to book a session",
            "phone_number": "+919999888877",
            "display_name": "Alia Bhatt",
        }

        msg1, created1 = ConversationService.store_inbound_message(payload)
        assert created1 is True
        conv = msg1.conversation
        assert conv.unread_count == 1

        # Second delivery of identical webhook
        msg2, created2 = ConversationService.store_inbound_message(payload)
        assert created2 is False
        assert msg1.id == msg2.id

        # Verify unread count was NOT incremented again
        conv.refresh_from_db()
        assert conv.unread_count == 1
        assert Message.objects.count() == 1

    def test_store_outbound_message(self):
        """Outbound messages update last_message_at without incrementing unread_count."""
        customer = Customer.objects.create(display_name="Ranbir Kapoor")
        conv = Conversation.objects.create(
            customer=customer,
            channel=Conversation.Channel.WHATSAPP,
            unread_count=2,
        )

        outbound_msg = ConversationService.store_outbound_message(
            conversation=conv,
            text="Sure! Here is our brochure.",
            external_message_id="wamid.outbound.002",
        )

        assert outbound_msg.direction == Message.Direction.OUTBOUND
        conv.refresh_from_db()
        assert conv.unread_count == 2  # Unchanged
        assert conv.last_message_preview == "Sure! Here is our brochure."

    def test_concurrent_duplicate_message_insertion(self):
        """
        Simulate 5 parallel threads processing the exact same webhook message simultaneously.
        Verifies all workers complete safely, exactly 1 message is stored, and no IntegrityError escapes.
        """
        external_msg_id = f"wamid.race_{uuid.uuid4().hex[:8]}"
        payload = {
            "channel": "WHATSAPP",
            "external_user_id": "918888777766",
            "external_message_id": external_msg_id,
            "text": "Concurrent message test",
            "phone_number": "+918888777766",
        }

        def worker_task(thread_id):
            close_old_connections()
            try:
                msg, created = ConversationService.store_inbound_message(payload)
                return msg.id, created
            finally:
                close_old_connections()

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        msg_ids = [res[0] for res in results]
        created_flags = [res[1] for res in results]

        assert len(set(msg_ids)) == 1, "All concurrent deliveries must resolve to the single message"
        assert created_flags.count(True) == 1, "Exactly one thread should have created the message"
        assert created_flags.count(False) == 4, "Remaining threads should have received existing message safely"
        assert Message.objects.filter(external_message_id=external_msg_id).count() == 1


@pytest.mark.django_db
class TestConversationAPI:
    def test_conversation_list_and_filters(self, authenticated_client):
        """Admin can list and filter conversations by channel, unread status, and customer."""
        cust1 = Customer.objects.create(display_name="Kareena Kapoor")
        conv1 = Conversation.objects.create(
            customer=cust1,
            channel=Conversation.Channel.INSTAGRAM,
            unread_count=3,
            last_message_at=timezone.now(),
        )

        cust2 = Customer.objects.create(display_name="Saif Ali Khan")
        conv2 = Conversation.objects.create(
            customer=cust2,
            channel=Conversation.Channel.WHATSAPP,
            unread_count=0,
            last_message_at=timezone.now(),
        )

        # 1. List all
        resp = authenticated_client.get("/api/v1/conversations/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["count"] == 2

        # 2. Filter by channel
        ig_resp = authenticated_client.get("/api/v1/conversations/?channel=INSTAGRAM")
        assert ig_resp.status_code == status.HTTP_200_OK
        assert ig_resp.json()["count"] == 1
        assert ig_resp.json()["results"][0]["id"] == str(conv1.id)

        # 3. Filter by unread
        unread_resp = authenticated_client.get("/api/v1/conversations/?unread=true")
        assert unread_resp.status_code == status.HTTP_200_OK
        assert unread_resp.json()["count"] == 1
        assert unread_resp.json()["results"][0]["unread_count"] == 3

    def test_conversation_messages_pagination(self, authenticated_client):
        """Admin can fetch paginated message history for a conversation."""
        customer = Customer.objects.create(display_name="Anushka Sharma")
        conv = Conversation.objects.create(
            customer=customer,
            channel=Conversation.Channel.WHATSAPP,
        )

        for i in range(5):
            Message.objects.create(
                conversation=conv,
                direction=Message.Direction.INBOUND if i % 2 == 0 else Message.Direction.OUTBOUND,
                text=f"Message number {i+1}",
                created_at=timezone.now(),
            )

        resp = authenticated_client.get(f"/api/v1/conversations/{conv.id}/messages/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 5
        assert len(data["results"]) == 5
        assert data["results"][0]["text"] == "Message number 1"

    def test_conversation_mark_read(self, authenticated_client):
        """Admin can mark a conversation as read, resetting unread_count to 0."""
        customer = Customer.objects.create(display_name="Virat Kohli")
        conv = Conversation.objects.create(
            customer=customer,
            channel=Conversation.Channel.WHATSAPP,
            unread_count=5,
        )

        read_resp = authenticated_client.post(f"/api/v1/conversations/{conv.id}/read/")
        assert read_resp.status_code == status.HTTP_200_OK
        assert read_resp.json()["unread_count"] == 0

        conv.refresh_from_db()
        assert conv.unread_count == 0

    def test_unauthenticated_conversations_rejected(self, api_client):
        """Unauthenticated requests are rejected with 401."""
        assert api_client.get("/api/v1/conversations/").status_code == status.HTTP_401_UNAUTHORIZED
