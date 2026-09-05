from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.customers.models import Customer, CustomerIdentity
from apps.leads.models import Lead
from apps.conversations.models import Conversation, Message

@pytest.fixture
def org_a():
    return make_organization(name="Org A")

@pytest.fixture
def org_b():
    return make_organization(name="Org B")

@pytest.fixture
def user_a(org_a):
    user = User.objects.create_user(email="usera@orga.com", password="password", is_active=True)
    OrganizationMembership.objects.create(organization=org_a, user=user, role="OWNER")
    user.is_staff = True
    user.save()
    return user

@pytest.fixture
def user_b(org_b):
    user = User.objects.create_user(email="userb@orgb.com", password="password", is_active=True)
    OrganizationMembership.objects.create(organization=org_b, user=user, role="OWNER")
    user.is_staff = True
    user.save()
    return user

@pytest.fixture
def api_client_a(user_a, org_a):
    client = APIClient()
    client.force_authenticate(user=user_a)
    client.defaults['HTTP_X_ORGANIZATION_ID'] = str(org_a.id)
    return client

@pytest.fixture
def api_client_b(user_b, org_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    client.defaults['HTTP_X_ORGANIZATION_ID'] = str(org_b.id)
    return client

@pytest.mark.django_db
def test_cross_tenant_lead_isolation(api_client_a, api_client_b, org_a, org_b):
    # Org A creates a Customer and a Lead
    customer_a = Customer.objects.create(organization=org_a, display_name="Customer A")
    lead_a = create_lead(organization=org_a, customer=customer_a, source_channel="WEBSITE", status="NEW")

    # User A can GET their lead
    response = api_client_a.get(f"/api/v1/leads/{lead_a.id}/")
    assert response.status_code == status.HTTP_200_OK

    # User B MUST NOT be able to GET User A's lead (IDOR protection)
    response = api_client_b.get(f"/api/v1/leads/{lead_a.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User B MUST NOT be able to UPDATE User A's lead
    response = api_client_b.patch(f"/api/v1/leads/{lead_a.id}/", {"notes": "Hacked"})
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # User B MUST NOT be able to DELETE User A's lead
    response = api_client_b.delete(f"/api/v1/leads/{lead_a.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_cross_tenant_customer_isolation(api_client_a, api_client_b, org_a):
    customer_a = Customer.objects.create(organization=org_a, display_name="Customer A")
    
    # User B attempting to access Customer A
    assert api_client_b.get(f"/api/v1/customers/{customer_a.id}/").status_code == status.HTTP_404_NOT_FOUND
    assert api_client_b.patch(f"/api/v1/customers/{customer_a.id}/", {"display_name": "Hacked"}).status_code == status.HTTP_404_NOT_FOUND
    assert api_client_b.delete(f"/api/v1/customers/{customer_a.id}/").status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_cross_tenant_assign_staff_idor(api_client_a, user_b, org_a, org_b):
    """
    Test IDOR vulnerability where Org A tries to assign a Lead to a User in Org B.
    """
    customer_a = Customer.objects.create(organization=org_a, display_name="Customer A")
    lead_a = create_lead(organization=org_a, customer=customer_a, source_channel="WEBSITE", status="NEW")
    
    # User A tries to assign User B (who is not in Org A) to their lead
    response = api_client_a.post(f"/api/v1/leads/{lead_a.id}/assign/", {"staff_id": str(user_b.id)})
    
    # Should fail with 404 because User B is not found within Org A's scope
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_cross_tenant_conversation_isolation(api_client_a, api_client_b, org_a):
    customer_a = Customer.objects.create(organization=org_a, display_name="Customer A")
    conv_a = Conversation.objects.create(organization=org_a, customer=customer_a, channel="INSTAGRAM")
    
    # User A can GET their conversation
    assert api_client_a.get(f"/api/v1/conversations/{conv_a.id}/").status_code == status.HTTP_200_OK

    # User B MUST NOT be able to GET User A's conversation
    assert api_client_b.get(f"/api/v1/conversations/{conv_a.id}/").status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_cross_tenant_outbound_dispatch_idor(api_client_a, api_client_b, org_a, org_b):
    """
    Test IDOR where User B attempts to send a message to a customer belonging to Org A
    by guessing their identity (e.g. phone number).
    """
    customer_a = Customer.objects.create(organization=org_a, display_name="Customer A")
    CustomerIdentity.objects.create(customer=customer_a, channel="WHATSAPP", external_user_id="123456789")

    # User B tries to dispatch to Org A's customer
    payload = {
        "channel": "WHATSAPP",
        "recipient_id": "123456789",
        "text": "Phishing message"
    }
    
    response = api_client_b.post("/api/v1/integrations/outbound-dispatch/", payload)
    # The message dispatch view silently drops if the customer is not found for the active org
    # Assuming the API succeeds silently, we must verify no message was created in Org A's scope by User B
    
    # Wait, the view actually returns 200 for async task dispatch even if not found?
    # Actually, the view logic updated in the security fix scopes the Customer.objects.filter(organization=request.organization).
    # If customer is None, it catches the error and creates no outbound message or task.
    # Let's verify no conversation/message was created for this dispatch.
    assert Conversation.objects.filter(customer=customer_a, messages__delivery_status="SENDING").count() == 0
