"""
Tests for Lead domain models, LeadDetectionService, deduplication, lifecycle activities, and APIs.
"""
import pytest
from django.utils import timezone
from rest_framework import status
from apps.accounts.models import User
from apps.conversations.models import Conversation, Message
from apps.conversations.services import ConversationService
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity, LeadTrigger
from apps.leads.services import LeadDetectionService, LeadManagementService
from apps.services.models import PhotographyService


@pytest.mark.django_db(transaction=True)
class TestLeadDetectionAndServices:
    @pytest.fixture
    def baby_shoot_service(self):
        return PhotographyService.objects.create(
            name="Newborn Baby Shoot",
            slug="newborn-baby-shoot",
            base_price=5000.00,
            duration_minutes=90,
        )

    @pytest.fixture
    def active_triggers(self, baby_shoot_service):
        t1 = LeadTrigger.objects.create(
            phrase="baby shoot",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=baby_shoot_service,
            priority=Lead.Priority.HIGH,
            is_active=True,
        )
        t2 = LeadTrigger.objects.create(
            phrase="book appointment",
            match_type=LeadTrigger.MatchType.CONTAINS,
            priority=Lead.Priority.URGENT,
            is_active=True,
        )
        t3 = LeadTrigger.objects.create(
            phrase=r"price|cost|rate",
            match_type=LeadTrigger.MatchType.REGEX,
            priority=Lead.Priority.MEDIUM,
            is_active=True,
        )
        return t1, t2, t3

    def test_contains_trigger_creates_lead(self, active_triggers, baby_shoot_service):
        """Inbound message matching CONTAINS trigger creates a Lead and LEAD_CREATED activity."""
        msg, _ = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_lead_001",
            "external_message_id": "ig_msg_001",
            "text": "Hello, I want to inquire about a baby shoot for next week!",
            "username": "meera_sharma",
            "display_name": "Meera Sharma",
        })

        lead, created, trigger = LeadDetectionService.process_inbound_message(msg)

        assert created is True
        assert lead is not None
        assert lead.customer.display_name == "Meera Sharma"
        assert lead.service == baby_shoot_service
        assert lead.status == Lead.Status.NEW
        assert lead.priority == Lead.Priority.HIGH
        assert lead.activities.count() == 1
        assert lead.activities.first().activity_type == LeadActivity.ActivityType.LEAD_CREATED

    def test_exact_trigger_creates_lead(self):
        """Exact match trigger matches whole normalized string."""
        trigger = LeadTrigger.objects.create(
            phrase="portfolio shoot",
            match_type=LeadTrigger.MatchType.EXACT,
            priority=Lead.Priority.URGENT,
            is_active=True,
        )
        msg, _ = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919111222333",
            "external_message_id": "wa_exact_01",
            "text": "Portfolio Shoot",
            "display_name": "Kabir Bedi",
        })
        lead, created, matched_trigger = LeadDetectionService.process_inbound_message(msg)
        assert created is True
        assert matched_trigger.id == trigger.id
        assert lead.priority == Lead.Priority.URGENT

    def test_regex_trigger_creates_lead(self, active_triggers):
        """Regex trigger matches pattern in text."""
        msg, _ = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_regex_01",
            "external_message_id": "ig_regex_msg_01",
            "text": "What is the hourly rate for a shoot?",
            "display_name": "Ananya Roy",
        })
        lead, created, matched_trigger = LeadDetectionService.process_inbound_message(msg)
        assert created is True
        assert matched_trigger.match_type == LeadTrigger.MatchType.REGEX

    def test_no_match_does_not_create_lead(self, active_triggers):
        """Messages with no matching intent keywords do not generate a lead."""
        msg, _ = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919876543211",
            "external_message_id": "wa_msg_nomatch",
            "text": "Good morning, thank you for the wonderful pictures!",
        })

        lead, created, trigger = LeadDetectionService.process_inbound_message(msg)

        assert lead is None
        assert created is False
        assert trigger is None
        assert Lead.objects.count() == 0

    def test_inactive_trigger_ignored(self, baby_shoot_service):
        """Inactive triggers are ignored during intent evaluation."""
        LeadTrigger.objects.create(
            phrase="wedding photography",
            match_type=LeadTrigger.MatchType.CONTAINS,
            service=baby_shoot_service,
            is_active=False,
        )

        msg, _ = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_inactive_test",
            "external_message_id": "ig_msg_inactive",
            "text": "Looking for wedding photography",
        })

        lead, created, _ = LeadDetectionService.process_inbound_message(msg)
        assert lead is None
        assert created is False

    def test_active_lead_deduplication_for_multiple_messages(self, active_triggers, baby_shoot_service):
        """
        Customer sends 3 messages during the same sales opportunity:
        1. 'baby shoot' -> Creates Lead
        2. 'what is the price?' -> Attaches MESSAGE_ATTACHED activity to existing Lead (no new lead)
        3. 'can I book tomorrow?' -> Attaches MESSAGE_ATTACHED activity to existing Lead (no new lead)
        """
        # Message 1
        msg1, _ = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919876543299",
            "external_message_id": "wa_seq_01",
            "text": "Hi, I am interested in a baby shoot",
            "display_name": "Rani Mukherjee",
        })
        lead1, created1, _ = LeadDetectionService.process_inbound_message(msg1)
        assert created1 is True
        assert Lead.objects.count() == 1

        # Message 2
        msg2, _ = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919876543299",
            "external_message_id": "wa_seq_02",
            "text": "what is the price?",
        })
        lead2, created2, _ = LeadDetectionService.process_inbound_message(msg2)
        assert created2 is False
        assert lead1.id == lead2.id
        assert Lead.objects.count() == 1  # No duplicate lead created!

        # Message 3
        msg3, _ = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919876543299",
            "external_message_id": "wa_seq_03",
            "text": "can I book appointment?",
        })
        lead3, created3, _ = LeadDetectionService.process_inbound_message(msg3)
        assert created3 is False
        assert lead1.id == lead3.id
        assert Lead.objects.count() == 1

        # Verify activity timeline on the single lead
        activities = list(lead1.activities.order_by("created_at"))
        assert len(activities) == 3
        assert activities[0].activity_type == LeadActivity.ActivityType.LEAD_CREATED
        assert activities[1].activity_type == LeadActivity.ActivityType.MESSAGE_ATTACHED
        assert activities[2].activity_type == LeadActivity.ActivityType.MESSAGE_ATTACHED

    def test_terminal_lead_allows_new_opportunity_subsequently(self, active_triggers, baby_shoot_service):
        """When an old lead reaches a terminal state (COMPLETED/LOST), subsequent inquiries create a fresh lead."""
        msg1, _ = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_cust_terminal",
            "external_message_id": "ig_msg_term_1",
            "text": "baby shoot",
            "display_name": "Siddharth Roy",
        })
        lead1, created1, _ = LeadDetectionService.process_inbound_message(msg1)
        assert created1 is True

        # Close first lead
        LeadManagementService.update_status(lead1, Lead.Status.COMPLETED)
        assert lead1.status == Lead.Status.COMPLETED
        assert lead1.closed_at is not None

        # Customer sends inquiry months later
        msg2, _ = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_cust_terminal",
            "external_message_id": "ig_msg_term_2",
            "text": "baby shoot for 1st birthday",
        })
        lead2, created2, _ = LeadDetectionService.process_inbound_message(msg2)
        assert created2 is True
        assert lead2.id != lead1.id
        assert Lead.objects.count() == 2


@pytest.mark.django_db
class TestLeadAPI:
    @pytest.fixture
    def sample_lead(self, admin_user):
        customer = Customer.objects.create(
            display_name="Tara Sutaria",
            primary_phone="+919777666555",
            email="tara@example.com",
        )
        service = PhotographyService.objects.create(
            name="Maternity Shoot",
            slug="maternity-shoot",
            base_price=8000.00,
        )
        lead = Lead.objects.create(
            customer=customer,
            source_channel="INSTAGRAM",
            service=service,
            status=Lead.Status.NEW,
            priority=Lead.Priority.HIGH,
            summary="Maternity photoshoot inquiry",
        )
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.LEAD_CREATED,
            description="Initial lead creation",
        )
        return lead

    def test_lead_list_and_filters(self, authenticated_client, sample_lead):
        """Admin can list and filter leads by status, source, and search."""
        resp = authenticated_client.get("/api/v1/leads/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["count"] == 1

        # Filter by status
        status_resp = authenticated_client.get("/api/v1/leads/?status=NEW")
        assert status_resp.status_code == status.HTTP_200_OK
        assert status_resp.json()["count"] == 1

        # Filter by non-matching status
        empty_resp = authenticated_client.get("/api/v1/leads/?status=LOST")
        assert empty_resp.status_code == status.HTTP_200_OK
        assert empty_resp.json()["count"] == 0

        # Search
        search_resp = authenticated_client.get("/api/v1/leads/?search=Tara")
        assert search_resp.status_code == status.HTTP_200_OK
        assert search_resp.json()["count"] == 1

    def test_lead_status_update_api(self, authenticated_client, sample_lead):
        """Admin can update status to QUALIFIED via POST /api/v1/leads/{id}/status/."""
        url = f"/api/v1/leads/{sample_lead.id}/status/"
        resp = authenticated_client.post(
            url,
            data={"status": "QUALIFIED", "notes": "Budget confirmed $800"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        sample_lead.refresh_from_db()
        assert sample_lead.status == "QUALIFIED"
        assert sample_lead.qualified_at is not None
        assert sample_lead.notes == "Budget confirmed $800"

        # Verify activity was logged
        activities = sample_lead.activities.filter(activity_type=LeadActivity.ActivityType.STATUS_CHANGED)
        assert activities.count() == 1

    def test_lead_assign_staff_api(self, authenticated_client, sample_lead, admin_user):
        """Admin can assign staff to lead via POST /api/v1/leads/{id}/assign/."""
        url = f"/api/v1/leads/{sample_lead.id}/assign/"
        resp = authenticated_client.post(
            url,
            data={"staff_id": str(admin_user.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        sample_lead.refresh_from_db()
        assert sample_lead.assigned_staff == admin_user

    def test_lead_activities_api(self, authenticated_client, sample_lead):
        """Admin can retrieve full activity timeline for a lead."""
        url = f"/api/v1/leads/{sample_lead.id}/activities/"
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 1
        assert resp.json()[0]["activity_type"] == "LEAD_CREATED"

    def test_lead_trigger_crud_api(self, authenticated_client):
        """Admin can manage lead trigger configuration via CRUD API."""
        # CREATE
        create_resp = authenticated_client.post(
            "/api/v1/leads/triggers/",
            data={
                "phrase": "birthday party",
                "match_type": "CONTAINS",
                "priority": "MEDIUM",
                "is_active": True,
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        trigger_id = create_resp.json()["id"]

        # LIST
        list_resp = authenticated_client.get("/api/v1/leads/triggers/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json()["count"] == 1

        # DELETE
        del_resp = authenticated_client.delete(f"/api/v1/leads/triggers/{trigger_id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT
        assert LeadTrigger.objects.count() == 0

    def test_unauthenticated_leads_rejected(self, api_client):
        """Unauthenticated requests are rejected with 401."""
        assert api_client.get("/api/v1/leads/").status_code == status.HTTP_401_UNAUTHORIZED
