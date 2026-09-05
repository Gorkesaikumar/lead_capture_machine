"""Dashboard routing metadata and admin analytics regression coverage."""
import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.organizations.models import OrganizationMembership
from tests.tenant_fixtures import make_organization

pytestmark = pytest.mark.django_db


def test_platform_admin_without_workspace_keeps_tenant_access_restricted():
    user = User.objects.create_superuser(email="platform@example.test", password="TestPassword!123")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get("/api/v1/auth/me/").json()["workspaces"] == []
    assert client.get("/api/v1/analytics/dashboard/").status_code == 403
    assert client.get("/api/v1/admin/kpis/").status_code == 200


def test_profile_exposes_only_active_accessible_workspaces():
    user = User.objects.create_user(email="member@example.test")
    active = make_organization(name="Active")
    revoked = make_organization(name="Revoked")
    inactive = make_organization(name="Inactive", is_active=False)
    deleted = make_organization(name="Deleted", is_deleted=True)
    make_organization(name="Unrelated")
    for org in [active, revoked, inactive, deleted]:
        OrganizationMembership.objects.create(
            organization=org, user=user, role="MEMBER", is_active=org != revoked,
        )
    client = APIClient()
    client.force_authenticate(user)
    assert client.get("/api/v1/auth/me/").json()["workspaces"] == [
        {"id": str(active.pk), "name": "Active", "role": "MEMBER"},
    ]
    assert client.get("/api/v1/analytics/dashboard/?preset=this_month").status_code == 200
    assert client.get("/api/v1/admin/kpis/").status_code == 403


def test_admin_analytics_counts_leads_using_source_channel(admin_user):
    org = make_organization()
    for channel in ["INSTAGRAM", "INSTAGRAM", "WHATSAPP", "WEBSITE", "MANUAL"]:
        customer = Customer.objects.create(organization=org, display_name=channel)
        Lead.objects.create(organization=org, customer=customer, source_channel=channel)
    client = APIClient()
    client.force_authenticate(admin_user)
    response = client.get("/api/v1/admin/analytics/?timeframe=30d")
    assert response.status_code == 200
    assert response.json()["lead_analytics"]["channel_breakdown"] == {
        "instagram": 2, "whatsapp": 1, "website": 1,
    }
