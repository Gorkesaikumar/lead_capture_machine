from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership, OrganizationInvitation

@pytest.fixture
def org():
    return make_organization(name="Test Org")

@pytest.fixture
def user_owner(org):
    user = User.objects.create_user(email="owner@org.com", password="password", is_active=True)
    OrganizationMembership.objects.create(organization=org, user=user, role="OWNER")
    return user

@pytest.fixture
def user_admin(org):
    user = User.objects.create_user(email="admin@org.com", password="password", is_active=True)
    OrganizationMembership.objects.create(organization=org, user=user, role="ADMIN")
    return user

@pytest.fixture
def user_member(org):
    user = User.objects.create_user(email="member@org.com", password="password", is_active=True)
    OrganizationMembership.objects.create(organization=org, user=user, role="MEMBER")
    return user

@pytest.fixture
def api_client_owner(user_owner, org):
    client = APIClient()
    client.force_authenticate(user=user_owner)
    client.defaults['HTTP_X_ORGANIZATION_ID'] = str(org.id)
    return client

@pytest.fixture
def api_client_admin(user_admin, org):
    client = APIClient()
    client.force_authenticate(user=user_admin)
    client.defaults['HTTP_X_ORGANIZATION_ID'] = str(org.id)
    return client

@pytest.fixture
def api_client_member(user_member, org):
    client = APIClient()
    client.force_authenticate(user=user_member)
    client.defaults['HTTP_X_ORGANIZATION_ID'] = str(org.id)
    return client

@pytest.mark.django_db
def test_organization_settings_rbac(api_client_owner, api_client_admin, api_client_member, org):
    # Member cannot update settings
    response = api_client_member.patch("/api/v1/organizations/current/", {"name": "Hacked"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Admin can update settings
    response = api_client_admin.patch("/api/v1/organizations/current/", {"name": "Updated by Admin"})
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_team_management_rbac(api_client_admin, api_client_member, user_member, org):
    # Get membership ID for user_member
    membership_id = OrganizationMembership.objects.get(user=user_member, organization=org).id
    
    # Member cannot remove someone
    response = api_client_member.delete(f"/api/v1/organizations/team/{membership_id}/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Admin can remove member
    response = api_client_admin.delete(f"/api/v1/organizations/team/{membership_id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT

@pytest.mark.django_db
def test_invitation_flow(api_client_admin, org):
    # Admin invites a user
    response = api_client_admin.post("/api/v1/organizations/invitations/", {
        "email": "newbie@org.com",
        "role": "MEMBER"
    })
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == "newbie@org.com"
    assert response.data["status"] == "PENDING"
    
    # Verify invitation created in DB
    invitation = OrganizationInvitation.objects.get(email="newbie@org.com")
    
    # Simulate a new user registering and accepting the invite
    new_user = User.objects.create_user(email="newbie@org.com", password="password", is_active=True)
    new_client = APIClient()
    new_client.force_authenticate(user=new_user)
    
    # Accept the invite
    accept_response = new_client.post("/api/v1/organizations/invitations/accept/", {
        "token": str(invitation.token)
    })
    assert accept_response.status_code == status.HTTP_200_OK
    
    # Verify user is now a member
    assert OrganizationMembership.objects.filter(user=new_user, organization=org, role="MEMBER").exists()
    
    # Verify invite is ACCEPTED
    invitation.refresh_from_db()
    assert invitation.status == "ACCEPTED"
