from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
from django.test import TransactionTestCase
from django.db import connection
from apps.customers.models import Customer
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
import threading

class ConversationUnreadCountIdempotencyTest(TransactionTestCase):
    def setUp(self):
        self.customer = Customer.objects.create(organization=test_workspace(),
            display_name="Test Customer",
            email="test@customer.com",
            primary_phone="+1234567890",
        )

        self.payload = {
            "channel": "WHATSAPP",
            "external_user_id": "1234567890",
            "external_message_id": "wamid.12345",
            "message_type": "TEXT",
            "text": "Hello there",
            "display_name": "Test",
        }

    def test_new_message_increments_unread_count(self):
        """A newly inserted inbound message should increment unread_count exactly once."""
        msg, created = ConversationService.store_inbound_message(self.payload, organization=test_workspace())
        self.assertTrue(created)
        
        conversation = msg.conversation
        self.assertEqual(conversation.unread_count, 1)

    def test_duplicate_message_id_does_not_increment_unread_count(self):
        """A duplicate external_message_id must not increment unread_count."""
        # First delivery
        msg1, created1 = ConversationService.store_inbound_message(self.payload, organization=test_workspace())
        self.assertTrue(created1)
        self.assertEqual(msg1.conversation.unread_count, 1)

        # Duplicate delivery
        msg2, created2 = ConversationService.store_inbound_message(self.payload, organization=test_workspace())
        self.assertFalse(created2)
        self.assertEqual(msg1.id, msg2.id)
        
        conversation = Conversation.objects.get(id=msg1.conversation.id)
        self.assertEqual(conversation.unread_count, 1)

    def test_concurrent_duplicate_processing(self):
        """
        Simulate two tasks simultaneously trying to store the exact same inbound message.
        """
        connection.close()
        
        results = []
        exceptions = []

        def worker():
            try:
                msg, created = ConversationService.store_inbound_message(self.payload, organization=test_workspace())
                results.append(created)
            except Exception as e:
                exceptions.append(e)
            finally:
                connection.close()

        thread1 = threading.Thread(target=worker)
        thread2 = threading.Thread(target=worker)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertEqual(len(exceptions), 0, f"Exceptions occurred: {exceptions}")
        self.assertEqual(len(results), 2)
        
        self.assertTrue(True in results)
        self.assertTrue(False in results)

        conversations = list(Conversation.objects.all())
        self.assertEqual(len(conversations), 1)
        
        # Verify unread_count is strictly 1
        self.assertEqual(conversations[0].unread_count, 1)
