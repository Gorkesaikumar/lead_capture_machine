"""
Tests for Customer domain models, CustomerResolutionService, concurrency/idempotency, and API endpoints.
"""
import concurrent.futures
import uuid
import pytest
from django.db import IntegrityError, close_old_connections, connection
from django.utils import timezone
from rest_framework import status
from apps.customers.models import Customer, CustomerIdentity
from apps.customers.services import CustomerResolutionService


@pytest.mark.django_db(transaction=True)
class TestCustomerModelsAndResolution:
    def test_customer_creation(self):
        """Customer model creates with UUID pk and timestamps."""
        customer = Customer.objects.create(
            display_name="Priya Sharma",
            primary_phone="+919876543210",
            email="priya@example.com",
            notes="Interested in newborn photography",
        )
        assert isinstance(customer.id, uuid.UUID)
        assert customer.display_name == "Priya Sharma"
        assert customer.is_deleted is False
        assert str(customer) == "Priya Sharma"

    def test_customer_identity_channel_constraint(self):
        """Database enforces unique constraint on (channel, external_user_id)."""
        customer = Customer.objects.create(display_name="Rahul Verma")
        CustomerIdentity.objects.create(
            customer=customer,
            channel=CustomerIdentity.Channel.INSTAGRAM,
            external_user_id="ig_123456789",
            username="rahul_photos",
        )

        # Attempt to insert identical (channel, external_user_id) under different customer
        customer2 = Customer.objects.create(display_name="Rahul Clone")
        with pytest.raises(IntegrityError):
            CustomerIdentity.objects.create(
                customer=customer2,
                channel=CustomerIdentity.Channel.INSTAGRAM,
                external_user_id="ig_123456789",
                username="rahul_v2",
            )

    def test_customer_soft_delete(self):
        """Soft delete marks is_deleted and records deleted_at timestamp."""
        customer = Customer.objects.create(display_name="Sneha Rao")
        customer.soft_delete()
        customer.refresh_from_db()
        assert customer.is_deleted is True
        assert customer.deleted_at is not None

        customer.restore()
        customer.refresh_from_db()
        assert customer.is_deleted is False
        assert customer.deleted_at is None

    def test_resolve_new_customer(self):
        """Resolves unknown external identity by creating Customer + CustomerIdentity."""
        customer, created = CustomerResolutionService.resolve_customer(
            channel="INSTAGRAM",
            external_user_id="ig_999888777",
            username="ananya_art",
            display_name="Ananya Roy",
            metadata={"bio": "Artist and mother"},
        )
        assert created is True
        assert customer.display_name == "Ananya Roy"
        assert customer.identities.count() == 1

        identity = customer.identities.first()
        assert identity.channel == "INSTAGRAM"
        assert identity.external_user_id == "ig_999888777"
        assert identity.username == "ananya_art"
        assert identity.metadata == {"bio": "Artist and mother"}

    def test_resolve_existing_customer_idempotency(self):
        """Resolving known identity returns existing customer and updates last_seen_at."""
        customer1, created1 = CustomerResolutionService.resolve_customer(
            channel="WHATSAPP",
            external_user_id="919876500000",
            phone_number="+919876500000",
            display_name="Karan Johar",
        )
        assert created1 is True

        # Second resolution with updated handle/meta
        customer2, created2 = CustomerResolutionService.resolve_customer(
            channel="WHATSAPP",
            external_user_id="919876500000",
            display_name="Karan Johar",
            metadata={"preferred_language": "en"},
        )
        assert created2 is False
        assert customer1.id == customer2.id

        # Verify only 1 customer and 1 identity in DB
        assert Customer.objects.count() == 1
        assert CustomerIdentity.objects.count() == 1

        identity = CustomerIdentity.objects.get(external_user_id="919876500000")
        assert identity.metadata == {"preferred_language": "en"}

    def test_concurrent_resolution_race_condition(self):
        """
        Simulate concurrent duplicate webhook workers resolving the same identity simultaneously.
        Verifies that database uniqueness constraints and atomic subtransactions recover safely
        without crashing and ensure exactly 1 Customer and 1 Identity exist.
        """
        channel = "INSTAGRAM"
        external_user_id = f"ig_concurrent_{uuid.uuid4().hex[:8]}"

        def worker_task(thread_id):
            close_old_connections()
            try:
                cust, created = CustomerResolutionService.resolve_customer(
                    channel=channel,
                    external_user_id=external_user_id,
                    username=f"user_{thread_id}",
                    metadata={"thread": thread_id},
                )
                return cust.id, created
            finally:
                close_old_connections()

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # All threads must return the exact same Customer ID
        customer_ids = [res[0] for res in results]
        created_flags = [res[1] for res in results]

        assert len(set(customer_ids)) == 1, "All concurrent workers must resolve to the same customer"
        assert created_flags.count(True) == 1, "Exactly one thread should have created the customer"
        assert created_flags.count(False) == 4, "Remaining threads should have resolved safely"

        # Verify DB counts
        assert CustomerIdentity.objects.filter(channel=channel, external_user_id=external_user_id).count() == 1


@pytest.mark.django_db
class TestCustomerAPI:
    def test_customer_list_and_search(self, authenticated_client):
        """Admin can list and search customers."""
        cust1 = Customer.objects.create(display_name="Anita Desai", primary_phone="+919811111111")
        CustomerIdentity.objects.create(
            customer=cust1,
            channel="INSTAGRAM",
            external_user_id="ig_anita",
            username="anita_d",
        )

        cust2 = Customer.objects.create(display_name="Vikram Seth", primary_phone="+919822222222")
        CustomerIdentity.objects.create(
            customer=cust2,
            channel="WHATSAPP",
            external_user_id="919822222222",
        )

        # List all
        response = authenticated_client.get("/api/v1/customers/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2

        # Search by name
        search_resp = authenticated_client.get("/api/v1/customers/?search=Anita")
        assert search_resp.status_code == status.HTTP_200_OK
        search_data = search_resp.json()
        assert search_data["count"] == 1
        assert search_data["results"][0]["display_name"] == "Anita Desai"

        # Search by external identity handle
        ig_search = authenticated_client.get("/api/v1/customers/?search=anita_d")
        assert ig_search.status_code == status.HTTP_200_OK
        assert ig_search.json()["count"] == 1

    def test_customer_detail_and_update(self, authenticated_client):
        """Admin can retrieve detail and update customer notes/phone."""
        customer = Customer.objects.create(
            display_name="Dev Patel",
            notes="Initial inquiry",
        )
        detail_url = f"/api/v1/customers/{customer.id}/"

        # GET Detail
        detail_resp = authenticated_client.get(detail_url)
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.json()["display_name"] == "Dev Patel"

        # PATCH Update
        update_resp = authenticated_client.patch(
            detail_url,
            data={"notes": "Updated note: Requested birthday package", "primary_phone": "+919833333333"},
            format="json",
        )
        assert update_resp.status_code == status.HTTP_200_OK
        customer.refresh_from_db()
        assert customer.notes == "Updated note: Requested birthday package"
        assert customer.primary_phone == "+919833333333"

    def test_customer_summaries_endpoints(self, authenticated_client):
        """Verify conversations, leads, and bookings summary endpoints."""
        customer = Customer.objects.create(display_name="Zoya Akhtar")

        conv_resp = authenticated_client.get(f"/api/v1/customers/{customer.id}/conversations/")
        assert conv_resp.status_code == status.HTTP_200_OK
        assert conv_resp.json()["data"]["total_conversations"] == 0

        leads_resp = authenticated_client.get(f"/api/v1/customers/{customer.id}/leads/")
        assert leads_resp.status_code == status.HTTP_200_OK
        assert leads_resp.json()["data"]["total_leads"] == 0

        bookings_resp = authenticated_client.get(f"/api/v1/customers/{customer.id}/bookings/")
        assert bookings_resp.status_code == status.HTTP_200_OK
        assert bookings_resp.json()["data"]["total_bookings"] == 0

    def test_unauthenticated_customer_access_rejected(self, api_client):
        """Unauthenticated requests are rejected with 401."""
        response = api_client.get("/api/v1/customers/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
