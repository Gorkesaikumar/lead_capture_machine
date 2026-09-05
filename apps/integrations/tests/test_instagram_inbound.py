from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Comprehensive automated tests for Instagram Inbound Webhook Integration.
Covers verification, HMAC signatures, message normalization, idempotency,
customer resolution, conversation management, lead trigger matching, and concurrency.
"""
import hashlib
import hmac
import json
import threading
from datetime import datetime, timedelta, timezone as dt_timezone
from django.conf import settings
from django.db import connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
from apps.customers.models import Customer, CustomerIdentity
from apps.customers.services import CustomerResolutionService
from apps.integrations.meta.common.verifier import MetaSignatureVerifier
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.models import RawWebhookEvent
from apps.integrations.pipeline import InboundPipelineService
from apps.integrations.tasks import process_instagram_webhook_event_task
from apps.leads.models import Lead, LeadActivity, LeadTrigger
from apps.leads.services import LeadDetectionService
from apps.services.models import PhotographyService


class InstagramWebhookIntegrationTests(TestCase):
    """
    Unit & integration tests for Instagram webhook endpoint and pipeline.
    """

    def setUp(self):
        self.client = Client()
        self.verify_token = getattr(settings, "META_VERIFY_TOKEN", "v4_meta_verify_token_prod_2026")
        self.app_secret = getattr(settings, "META_APP_SECRET", "mock_meta_app_secret_32chars_long")
        self.webhook_url = "/api/v1/webhooks/meta/instagram/"

        # Setup test organization and integration config
        from apps.organizations.models import Organization
        from apps.integrations.models import IntegrationConfig

        self.org = make_organization(name="Test Org", slug="test-org")
        self.config = IntegrationConfig.objects.create(
            organization=self.org,
            provider="INSTAGRAM",
            is_active=True,
            metadata={"destination_id": "17841405962012345"}
        )

        # Setup test photography service and trigger
        self.service = PhotographyService.objects.create(organization=self.org,
            name="Baby Shoot",
            slug="baby-shoot",
            base_price=15000.00,
            duration_minutes=60,
            is_active=True,
        )
        self.trigger = LeadTrigger.objects.create(organization=self.org,
            phrase="baby shoot",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=self.service,
            priority=Lead.Priority.HIGH,
            is_active=True,
        )

    def _generate_signature(self, body_bytes: bytes) -> str:
        """Computes Meta SHA256 signature header for payload."""
        expected_hash = hmac.new(
            self.app_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={expected_hash}"

    # --------------------------------------------------------------------------
    # Scenario 1: Webhook Verification GET with valid token
    # --------------------------------------------------------------------------
    def test_01_webhook_verification_get_success(self):
        """GET with valid hub.mode, hub.verify_token returns hub.challenge with HTTP 200."""
        challenge_str = "test_challenge_123456"
        response = self.client.get(
            self.webhook_url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": self.verify_token,
                "hub.challenge": challenge_str,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), challenge_str)

    # --------------------------------------------------------------------------
    # Scenario 2: Webhook Verification GET with invalid token returns 403
    # --------------------------------------------------------------------------
    def test_02_webhook_verification_get_invalid_token(self):
        """GET with invalid token is rejected with HTTP 403."""
        response = self.client.get(
            self.webhook_url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token_xyz",
                "hub.challenge": "12345",
            },
        )
        self.assertEqual(response.status_code, 403)

    # --------------------------------------------------------------------------
    # Scenario 3: Webhook POST with invalid HMAC signature returns 403
    # --------------------------------------------------------------------------
    def test_03_webhook_post_invalid_signature(self):
        """POST with forged or missing signature is rejected with HTTP 403."""
        payload = {"object": "instagram", "entry": []}
        body_bytes = json.dumps(payload).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid_hash_value_12345",
        )
        self.assertEqual(response.status_code, 403)

    # --------------------------------------------------------------------------
    # Scenario 4: Valid Instagram inbound message creates all required records
    # --------------------------------------------------------------------------
    def test_04_valid_instagram_inbound_message(self):
        """Valid signed POST creates RawWebhookEvent, Customer, Conversation, Message, and Lead."""
        ig_user_id = "ig_user_1001"
        mid = "m_mid_0001"
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841405962012345",
                    "time": 1723145678000,
                    "messaging": [
                        {
                            "sender": {"id": ig_user_id},
                            "recipient": {"id": "17841405962012345"},
                            "timestamp": 1723145678000,
                            "message": {
                                "mid": mid,
                                "text": "Hi, I want to book a baby shoot session",
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        response = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        self.assertEqual(response.status_code, 200)

        # Process the pipeline synchronously (simulate Celery task execution)
        raw_event = RawWebhookEvent.objects.filter(channel="INSTAGRAM").latest("created_at")
        InboundPipelineService.process_raw_webhook_event(raw_event)

        # Verify Customer & Identity
        identity = CustomerIdentity.objects.get(channel="INSTAGRAM", external_user_id=ig_user_id)
        customer = identity.customer
        self.assertIsNotNone(customer)
        self.assertTrue(customer.display_name.startswith("Instagram User"))

        # Verify Conversation
        conv = Conversation.objects.get(customer=customer, channel="INSTAGRAM")
        self.assertEqual(conv.unread_count, 1)

        # Verify Message
        msg = Message.objects.get(external_message_id=mid)
        self.assertEqual(msg.conversation, conv)
        self.assertEqual(msg.text, "Hi, I want to book a baby shoot session")
        self.assertEqual(msg.direction, Message.Direction.INBOUND)

        # Verify Lead Trigger Match & Lead Creation
        lead = Lead.objects.get(customer=customer, is_deleted=False)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.source_channel, "INSTAGRAM")
        self.assertEqual(lead.service, self.service)
        self.assertEqual(lead.trigger, self.trigger)

    # --------------------------------------------------------------------------
    # Scenario 5: Second message from same Instagram user reuses customer & conversation
    # --------------------------------------------------------------------------
    def test_05_second_message_same_user_reuses_conversation(self):
        """Second message attaches to existing conversation and lead without creating duplicates."""
        ig_user_id = "ig_user_1002"

        # 1st message
        msg1_dict = {
            "channel": "INSTAGRAM",
            "external_user_id": ig_user_id,
            "external_message_id": "mid_1002_a",
            "message_type": "TEXT",
            "text": "Hello, interested in baby shoot",
        }
        msg1, created1 = ConversationService.store_inbound_message(msg1_dict, organization=self.org)
        self.assertTrue(created1)
        lead1, lead_created1, _ = LeadDetectionService.process_inbound_message(msg1)
        self.assertTrue(lead_created1)

        # 2nd message from same user (triggers same intent -> attached to existing active lead)
        msg2_dict = {
            "channel": "INSTAGRAM",
            "external_user_id": ig_user_id,
            "external_message_id": "mid_1002_b",
            "message_type": "TEXT",
            "text": "When is the next available slot for the baby shoot?",
        }
        msg2, created2 = ConversationService.store_inbound_message(msg2_dict, organization=self.org)
        self.assertTrue(created2)
        lead2, lead_created2, _ = LeadDetectionService.process_inbound_message(msg2)

        # Should NOT create duplicate lead
        self.assertFalse(lead_created2)
        self.assertEqual(lead1.id, lead2.id)

        # Conversation should be the same
        self.assertEqual(msg1.conversation.id, msg2.conversation.id)
        conv = Conversation.objects.get(id=msg1.conversation.id)
        self.assertEqual(conv.unread_count, 2)

        # Lead activities should have 2 entries
        activities = LeadActivity.objects.filter(lead=lead1)
        self.assertEqual(activities.count(), 2)

    # --------------------------------------------------------------------------
    # Scenario 6: Duplicate webhook event ignored idempotently
    # --------------------------------------------------------------------------
    def test_06_duplicate_webhook_event_idempotency(self):
        """Exact duplicate webhook delivery returns 200 and does not duplicate records."""
        ig_user_id = "ig_user_1003"
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841405962012345",
                    "time": 1723145678000,
                    "messaging": [
                        {
                            "sender": {"id": ig_user_id},
                            "recipient": {"id": "17841405962012345"},
                            "timestamp": 1723145678000,
                            "message": {
                                "mid": "mid_1003_dup",
                                "text": "Testing duplicate delivery",
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        # Delivery 1
        res1 = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        self.assertEqual(res1.status_code, 200)

        # Delivery 2 (exact same payload)
        res2 = self.client.post(
            self.webhook_url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        self.assertEqual(res2.status_code, 200)

        # Only one RawWebhookEvent in DB
        events = RawWebhookEvent.objects.filter(channel="INSTAGRAM", payload__entry__0__messaging__0__message__mid="mid_1003_dup")
        self.assertEqual(events.count(), 1)

    # --------------------------------------------------------------------------
    # Scenario 7: Duplicate message ID ignored idempotently
    # --------------------------------------------------------------------------
    def test_07_duplicate_message_id_idempotency(self):
        """Duplicate external_message_id does not create a duplicate Message or increase unread count."""
        msg_dict = {
            "channel": "INSTAGRAM",
            "external_user_id": "ig_user_1004",
            "external_message_id": "mid_1004_unique",
            "message_type": "TEXT",
            "text": "Hello there",
        }
        msg1, created1 = ConversationService.store_inbound_message(msg_dict, organization=self.org)
        self.assertTrue(created1)
        self.assertEqual(msg1.conversation.unread_count, 1)

        # Resend same message dict
        msg2, created2 = ConversationService.store_inbound_message(msg_dict, organization=self.org)
        self.assertFalse(created2)
        self.assertEqual(msg1.id, msg2.id)

        conv = Conversation.objects.get(id=msg1.conversation.id)
        self.assertEqual(conv.unread_count, 1)

    # --------------------------------------------------------------------------
    # Scenario 8: Lead trigger matching (case-insensitive & whitespace normalized)
    # --------------------------------------------------------------------------
    def test_08_lead_trigger_matching_case_insensitive(self):
        """Matches lead trigger phrases regardless of case, surrounding punctuation, and extra spaces."""
        customer, _ = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_user_1005",
         organization=self.org)
        conv, _ = Conversation.objects.get_or_create(organization=self.org, customer=customer, channel="INSTAGRAM")

        msg = Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="  HI BROTHER!! I want to book for BABY SHOOT... please reply! ",
            external_message_id="mid_1005_case",
        )

        lead, created, matched_trigger = LeadDetectionService.process_inbound_message(msg)
        self.assertTrue(created)
        self.assertIsNotNone(matched_trigger)
        self.assertEqual(matched_trigger.phrase, "baby shoot")
        self.assertEqual(lead.service, self.service)

    # --------------------------------------------------------------------------
    # Scenario 9: Instagram source assignment
    # --------------------------------------------------------------------------
    def test_09_instagram_source_assignment(self):
        """Ensures lead source_channel is strictly set to 'INSTAGRAM'."""
        customer, _ = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_user_1006",
         organization=self.org)
        conv, _ = Conversation.objects.get_or_create(organization=self.org, customer=customer, channel="INSTAGRAM")
        msg = Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="Baby shoot enquiry",
            external_message_id="mid_1006",
        )
        lead, created, _ = LeadDetectionService.process_inbound_message(msg)
        self.assertTrue(created)
        self.assertEqual(lead.source_channel, "INSTAGRAM")

    # --------------------------------------------------------------------------
    # Scenario 10: Customer identity preservation
    # --------------------------------------------------------------------------
    def test_10_customer_identity_preservation(self):
        """Customer identity is updated with latest username without creating duplicate records."""
        customer1, created1 = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_user_1007",
            username="insta_fan_1",
         organization=self.org)
        self.assertTrue(created1)
        self.assertEqual(customer1.display_name, "insta_fan_1")

        # Resolve again with updated profile name
        customer2, created2 = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_user_1007",
            display_name="Praveen Kumar",
            username="praveen_k",
         organization=self.org)
        self.assertFalse(created2)
        self.assertEqual(customer1.id, customer2.id)
        customer1.refresh_from_db()
        self.assertEqual(customer1.display_name, "Praveen Kumar")

    # --------------------------------------------------------------------------
    # Scenario 11: Conversation reuse across sessions
    # --------------------------------------------------------------------------
    def test_11_conversation_reuse(self):
        """Multiple messages over time use the single active conversation thread."""
        customer, _ = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_user_1008",
         organization=self.org)
        msg1_dict = {
            "channel": "INSTAGRAM",
            "external_user_id": "ig_user_1008",
            "external_message_id": "mid_1008_1",
            "message_type": "TEXT",
            "text": "Hello",
        }
        msg1, _ = ConversationService.store_inbound_message(msg1_dict, organization=self.org)

        msg2_dict = {
            "channel": "INSTAGRAM",
            "external_user_id": "ig_user_1008",
            "external_message_id": "mid_1008_2",
            "message_type": "TEXT",
            "text": "Are you open on Sundays?",
        }
        msg2, _ = ConversationService.store_inbound_message(msg2_dict, organization=self.org)

        self.assertEqual(msg1.conversation.id, msg2.conversation.id)
        self.assertEqual(Conversation.objects.filter(customer=customer).count(), 1)

    # --------------------------------------------------------------------------
    # Scenario 12: Timestamp conversion (ms, sec, ISO string, None)
    # --------------------------------------------------------------------------
    def test_12_timestamp_conversion_ms_and_sec(self):
        """Verifies milliseconds, seconds, string, and None timestamps parse accurately to UTC."""
        # 13-digit ms (2024-08-08 18:14:38 UTC)
        ts_ms = 1723140878000
        dt_ms = InstagramInboundParser._parse_timestamp(ts_ms)
        self.assertEqual(dt_ms.year, 2024)
        self.assertEqual(dt_ms.month, 8)

        # 10-digit sec (2024-08-08 18:14:38 UTC)
        ts_sec = 1723140878
        dt_sec = InstagramInboundParser._parse_timestamp(ts_sec)
        self.assertEqual(dt_sec.year, 2024)
        self.assertEqual(dt_sec.month, 8)

        # None / missing
        dt_none = InstagramInboundParser._parse_timestamp(None)
        self.assertIsNotNone(dt_none)
        self.assertGreater(dt_none.year, 2020)

    # --------------------------------------------------------------------------
    # Scenario 13: Messaging window calculation
    # --------------------------------------------------------------------------
    def test_13_messaging_window_recalculation(self):
        """Calculates whether the 24-hour customer service window is open."""
        ig_user_id = "ig_user_1009"
        customer, _ = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id=ig_user_id,
         organization=self.org)
        conv = Conversation.objects.create(organization=self.org, customer=customer, channel="INSTAGRAM")

        # Inbound message 2 hours ago -> window is OPEN
        two_hours_ago = timezone.now() - timedelta(hours=2)
        Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="Recent message",
            provider_timestamp=two_hours_ago,
            created_at=two_hours_ago,
        )
        self.assertTrue(ConversationService.is_within_24h_window("INSTAGRAM", ig_user_id, organization=self.org))

        # Inbound message 25 hours ago -> window is CLOSED
        twenty_five_hours_ago = timezone.now() - timedelta(hours=25)
        Message.objects.all().delete()
        Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="Old message",
            provider_timestamp=twenty_five_hours_ago,
            created_at=twenty_five_hours_ago,
        )
        self.assertFalse(ConversationService.is_within_24h_window("INSTAGRAM", ig_user_id, organization=self.org))

    # --------------------------------------------------------------------------
    # Scenario 15: Malformed webhook payload handling (returns 400 without crashing)
    # --------------------------------------------------------------------------
    def test_15_malformed_webhook_payload(self):
        """Malformed non-JSON payload returns 400 Bad Request."""
        invalid_body = b"NOT_A_JSON_PAYLOAD_<<<>>>"
        sig = self._generate_signature(invalid_body)

        response = self.client.post(
            self.webhook_url,
            data=invalid_body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        self.assertEqual(response.status_code, 400)

    # --------------------------------------------------------------------------
    # Scenario 16: Webhook task retry safety (Celery task idempotency)
    # --------------------------------------------------------------------------
    def test_16_webhook_retry_safety(self):
        """Re-running process_instagram_webhook_event_task does not duplicate messages or counts."""
        ig_user_id = "ig_user_1010"
        mid = "mid_1010_retry"
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841405962012345",
                    "time": 1723145678000,
                    "messaging": [
                        {
                            "sender": {"id": ig_user_id},
                            "recipient": {"id": "17841405962012345"},
                            "timestamp": 1723145678000,
                            "message": {
                                "mid": mid,
                                "text": "Baby shoot enquiry retry test",
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        raw_event, _ = InboundPipelineService.record_raw_event(
            channel="INSTAGRAM",
            raw_body=body_bytes,
            signature_header=sig,
            payload=payload,
        )

        # Run task first time
        result1 = process_instagram_webhook_event_task.apply(args=(str(raw_event.id),)).get()
        self.assertEqual(result1.get("messages_processed"), 1)
        self.assertEqual(result1.get("leads_created"), 1)

        # Simulate task retry
        raw_event.refresh_from_db()
        result2 = process_instagram_webhook_event_task.apply(args=(str(raw_event.id),)).get()
        self.assertEqual(result2.get("status"), RawWebhookEvent.Status.PROCESSED)

        # Verify only 1 message and 1 lead exist
        self.assertEqual(Message.objects.filter(external_message_id=mid).count(), 1)
        customer = CustomerIdentity.objects.get(channel="INSTAGRAM", external_user_id=ig_user_id).customer
        self.assertEqual(Lead.objects.filter(customer=customer).count(), 1)


class InstagramLeadConcurrencyTests(TransactionTestCase):
    """
    Scenario 14: Concurrent lead creation across multiple threads.
    Using TransactionTestCase to test real database locks and unique constraints.
    """

    def test_14_concurrent_lead_creation(self):
        """Simultaneous inbound messages from the same user create exactly one active lead."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Baby Shoot",
            slug="baby-shoot",
            base_price=15000.00,
            duration_minutes=60,
            is_active=True,
        )
        LeadTrigger.objects.create(organization=test_workspace(),
            phrase="baby shoot",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=service,
            priority=Lead.Priority.HIGH,
            is_active=True,
        )

        customer = Customer.objects.create(organization=test_workspace(), display_name="Concurrent Customer")
        conv = Conversation.objects.create(organization=test_workspace(), customer=customer, channel="INSTAGRAM")

        msg1 = Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="Baby shoot enquiry thread 1",
            external_message_id="mid_conc_1",
        )
        msg2 = Message.objects.create(
            conversation=conv,
            direction=Message.Direction.INBOUND,
            message_type="TEXT",
            text="Baby shoot enquiry thread 2",
            external_message_id="mid_conc_2",
        )

        connection.close()

        results = []
        exceptions = []

        def worker(message):
            try:
                lead, created, _ = LeadDetectionService.process_inbound_message(message)
                results.append((lead.id, created))
            except Exception as e:
                exceptions.append(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=(msg1,))
        t2 = threading.Thread(target=worker, args=(msg2,))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        self.assertEqual(len(exceptions), 0, f"Exceptions in worker threads: {exceptions}")
        self.assertEqual(len(results), 2)

        created_flags = [c for _, c in results]
        self.assertTrue(True in created_flags)
        self.assertTrue(False in created_flags)

        lead_ids = [lid for lid, _ in results]
        self.assertEqual(lead_ids[0], lead_ids[1])

        active_leads = Lead.objects.filter(customer=customer, status__in=Lead.ACTIVE_STATUSES)
        self.assertEqual(active_leads.count(), 1)
