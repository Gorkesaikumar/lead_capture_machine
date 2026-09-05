import json
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership

def run_tests():
    print("Starting Phase 2 Tests...")
    
    # 1. Setup Test Data
    # Clear existing test data
    Organization.objects.filter(slug__startswith="test-org").delete()
    Organization.objects.filter(owner__email__endswith="@test.com").delete()
    User.objects.filter(email__endswith="@test.com").delete()

    owner = User.objects.create_user(email="owner@test.com", password="password", full_name="Owner User")
    admin = User.objects.create_user(email="admin@test.com", password="password", full_name="Admin User")
    member = User.objects.create_user(email="member@test.com", password="password", full_name="Member User")
    outsider = User.objects.create_user(email="outsider@test.com", password="password", full_name="Outsider User")

    org = Organization.objects.create(name="Test Org", slug="test-org-1", owner=owner)
    
    OrganizationMembership.objects.create(organization=org, user=owner, role="OWNER")
    OrganizationMembership.objects.create(organization=org, user=admin, role="ADMIN")
    OrganizationMembership.objects.create(organization=org, user=member, role="MEMBER")

    client_owner = APIClient()
    client_owner.force_authenticate(user=owner)
    
    client_admin = APIClient()
    client_admin.force_authenticate(user=admin)
    
    client_member = APIClient()
    client_member.force_authenticate(user=member)
    
    client_outsider = APIClient()
    client_outsider.force_authenticate(user=outsider)

    client_anon = APIClient()

    results = []
    
    # 2. Test Organization Context Header
    print("Testing Organization header context...")
    # Owner accessing leads without header should still work (fallback to first active membership)
    res = client_owner.get("/api/v1/leads/", HTTP_HOST="localhost")
    results.append(f"Owner access without header: {res.status_code}")
    
    # 3. Test Member accessing Admin-only route (Triggers)
    print("Testing Admin-only routes...")
    res = client_member.get("/api/v1/leads/triggers/", HTTP_X_ORGANIZATION_ID=str(org.id), HTTP_HOST="localhost")
    results.append(f"Member accessing triggers: {res.status_code}") # Should be 403
    
    res = client_admin.get("/api/v1/leads/triggers/", HTTP_X_ORGANIZATION_ID=str(org.id), HTTP_HOST="localhost")
    results.append(f"Admin accessing triggers: {res.status_code}") # Should be 200

    # 4. Test Cross-Tenant Data Access
    print("Testing Cross-Tenant Data Access...")
    res = client_outsider.get("/api/v1/leads/", HTTP_X_ORGANIZATION_ID=str(org.id), HTTP_HOST="localhost")
    results.append(f"Outsider accessing org leads: {res.status_code}") # Should be 403

    # Create a lead in org
    from apps.leads.models import Lead
    from apps.customers.models import Customer
    customer = Customer.objects.create(organization=org, name="Test Customer", phone_number="+1234567890")
    lead = Lead.objects.create(organization=org, source_channel="WEBSITE", customer=customer)
    
    res = client_outsider.get(f"/api/v1/leads/{lead.id}/", HTTP_X_ORGANIZATION_ID=str(org.id), HTTP_HOST="localhost")
    results.append(f"Outsider accessing specific org lead: {res.status_code}") # Should be 404 or 403

    print("\n--- TEST RESULTS ---")
    for r in results:
        print(r)

import django
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

run_tests()
