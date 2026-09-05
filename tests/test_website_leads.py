from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.organizations.models import Organization
from apps.leads.models import LeadForm, Lead
from apps.customers.models import Customer

@pytest.fixture
def org():
    return make_organization(name="Studio V4")

@pytest.fixture
def lead_form(org):
    return LeadForm.objects.create(
        organization=org,
        name="Main Contact Form",
        is_active=True,
        success_message="Thanks!"
    )

@pytest.fixture
def disabled_form(org):
    return LeadForm.objects.create(
        organization=org,
        name="Old Campaign",
        is_active=False
    )

@pytest.fixture
def public_client():
    return APIClient()

@pytest.mark.django_db
class TestWebsiteLeadsPublicAPI:
    
    def test_valid_form_submission_creates_lead(self, public_client, lead_form, org):
        payload = {
            "name": "Jane Doe",
            "phone": "+1234567890",
            "email": "jane@example.com",
            "message": "I'd like to book a shoot"
        }
        
        response = public_client.post(f"/api/v1/forms/{lead_form.public_id}/submit/", payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        
        # Verify Lead and Customer were created correctly
        lead = Lead.objects.get()
        assert lead.organization == org
        assert lead.source_channel == "WEBSITE"
        assert lead.status == "NEW"
        
        customer = lead.customer
        assert customer.organization == org
        assert customer.display_name == "Jane Doe"
        assert customer.primary_phone == "+1234567890"
        assert customer.email == "jane@example.com"
        
        # Verify the lead note has the message
        assert "I'd like to book a shoot" in lead.notes
        
    def test_missing_required_fields_rejected(self, public_client, lead_form):
        # Missing 'name' and 'phone'
        payload = {
            "email": "jane@example.com"
        }
        
        response = public_client.post(f"/api/v1/forms/{lead_form.public_id}/submit/", payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data
        
    def test_disabled_form_rejects_submission(self, public_client, disabled_form):
        payload = {
            "name": "Jane Doe",
            "phone": "+1234567890"
        }
        
        response = public_client.post(f"/api/v1/forms/{disabled_form.public_id}/submit/", payload)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "This form is currently inactive."
        
    def test_submission_to_nonexistent_form_404(self, public_client):
        import uuid
        payload = {
            "name": "Jane Doe",
            "phone": "+1234567890"
        }
        
        response = public_client.post(f"/api/v1/forms/{uuid.uuid4()}/submit/", payload)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
    def test_rate_limiting_public_form(self, public_client, lead_form):
        """
        The PublicLeadSubmissionThrottle is configured for 10/min.
        We submit 11 times and expect the 11th to fail with 429 Too Many Requests.
        """
        payload = {
            "name": "Spammer",
            "phone": "+1000000000"
        }
        
        # We need to explicitly enable throttling for testing by overriding settings
        # if the test runner doesn't have it enabled, but assuming it's active:
        from django.core.cache import cache
        cache.clear()
        
        for _ in range(10):
            res = public_client.post(f"/api/v1/forms/{lead_form.public_id}/submit/", payload)
            assert res.status_code == status.HTTP_201_CREATED
            
        # 11th request should be rate-limited
        res = public_client.post(f"/api/v1/forms/{lead_form.public_id}/submit/", payload)
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
