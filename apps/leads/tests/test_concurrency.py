import threading
from django.test import TransactionTestCase
from django.db import connection, transaction
from apps.customers.models import Customer
from apps.conversations.models import Conversation, Message
from apps.leads.models import Lead, LeadTrigger, LeadActivity
from apps.leads.services import LeadDetectionService

class LeadDetectionConcurrencyTest(TransactionTestCase):
    """
    Tests for concurrency race conditions in LeadDetectionService.
    Using TransactionTestCase because threads need to interact with actual DB commits.
    """

    def setUp(self):
        # Create a customer
        self.customer = Customer.objects.create(
            display_name="Test Customer",
            email="test@customer.com",
            primary_phone="+1234567890",
        )
        
        # Create a trigger
        self.trigger = LeadTrigger.objects.create(
            phrase="book a session",
            match_type=LeadTrigger.MatchType.CONTAINS,
            is_active=True
        )

        # Create two concurrent conversations (or one, but two messages)
        self.conversation = Conversation.objects.create(
            customer=self.customer,
            channel="WHATSAPP",
            external_thread_id="12345"
        )
        
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            message_type="TEXT",
            direction="INBOUND",
            text="I want to book a session",
            external_message_id="msg1"
        )
        
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            message_type="TEXT",
            direction="INBOUND",
            text="Also, book a session for my friend",
            external_message_id="msg2"
        )

    def test_concurrent_lead_creation(self):
        """
        Simulate two requests processing messages concurrently for the same customer.
        Only ONE active lead should be created.
        """
        # Close old connections to ensure threads get their own DB connections
        connection.close()

        results = []
        exceptions = []

        def worker(message):
            try:
                # We need to manually close the connection at the end of the thread
                # but django handles it mostly. To be safe, we let django manage it.
                lead, created, trigger = LeadDetectionService.process_inbound_message(message)
                results.append((lead.id, created))
            except Exception as e:
                exceptions.append(e)
            finally:
                connection.close()

        thread1 = threading.Thread(target=worker, args=(self.message1,))
        thread2 = threading.Thread(target=worker, args=(self.message2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # No exceptions should have occurred
        self.assertEqual(len(exceptions), 0, f"Exceptions occurred in threads: {exceptions}")
        
        # We should have exactly 2 successful results
        self.assertEqual(len(results), 2)
        
        # Exactly one should have 'created == True', the other 'created == False'
        created_flags = [created for _, created in results]
        self.assertTrue(True in created_flags)
        self.assertTrue(False in created_flags)
        
        # Both should point to the SAME lead ID
        lead_ids = [lead_id for lead_id, _ in results]
        self.assertEqual(lead_ids[0], lead_ids[1])
        
        # Check DB state
        active_leads = Lead.objects.filter(customer=self.customer, status__in=Lead.ACTIVE_STATUSES)
        self.assertEqual(active_leads.count(), 1)
        
        # Check LeadActivity state
        activities = LeadActivity.objects.filter(lead_id=lead_ids[0]).order_by("created_at")
        
        # There should be 1 LEAD_CREATED and 1 MESSAGE_ATTACHED (order may vary based on thread execution speed)
        activity_types = [act.activity_type for act in activities]
        self.assertIn(LeadActivity.ActivityType.LEAD_CREATED, activity_types)
        self.assertIn(LeadActivity.ActivityType.MESSAGE_ATTACHED, activity_types)
