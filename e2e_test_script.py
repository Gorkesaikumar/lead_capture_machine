import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django
django.setup()

from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadForm
from apps.conversations.models import Conversation, Message
from apps.integrations.models import IntegrationConfig
from apps.subscriptions.models import Subscription, Plan

def run_e2e():
    report = {"PASS": [], "FAIL": [], "BLOCKER": [], "HIGH": [], "MEDIUM": [], "LOW": []}

    client_a = APIClient(HTTP_HOST="localhost")
    client_b = APIClient(HTTP_HOST="localhost")

    try:
        print("Setting up Organizations, Users, and Memberships...")
        # Plan
        free_plan, _ = Plan.objects.get_or_create(code="FREE", defaults={"name": "Free", "max_users": 2})

        # Org A
        user_a_stub = User.objects.create_user(email="usera@example.com", password="Password123!", full_name="User A")
        org_a = Organization.objects.create(name="Studio A", slug="studio-a", owner=user_a_stub)
        user_a_stub.organization = org_a
        user_a_stub.save()
        OrganizationMembership.objects.create(organization=org_a, user=user_a_stub, role=OrganizationMembership.Role.OWNER, is_active=True)
        sub_a = Subscription.objects.create(organization=org_a, plan=free_plan, status=Subscription.Status.ACTIVE)
        
        # Org B
        user_b_stub = User.objects.create_user(email="userb@example.com", password="Password123!", full_name="User B")
        org_b = Organization.objects.create(name="Studio B", slug="studio-b", owner=user_b_stub)
        user_b_stub.organization = org_b
        user_b_stub.save()
        OrganizationMembership.objects.create(organization=org_b, user=user_b_stub, role=OrganizationMembership.Role.OWNER, is_active=True)
        sub_b = Subscription.objects.create(organization=org_b, plan=free_plan, status=Subscription.Status.ACTIVE)

        # Login
        resp_a = client_a.post("/api/v1/auth/login/", {"email": "usera@example.com", "password": "Password123!"})
        if resp_a.status_code != 200:
            report["BLOCKER"].append(f"Login failed for User A: {resp_a.data}")
            return report
        token_a = resp_a.json()["data"]["token"]
        client_a.credentials(HTTP_AUTHORIZATION=f"Token {token_a}")

        resp_b = client_b.post("/api/v1/auth/login/", {"email": "userb@example.com", "password": "Password123!"})
        token_b = resp_b.json()["data"]["token"]
        client_b.credentials(HTTP_AUTHORIZATION=f"Token {token_b}")

        report["PASS"].append("Auth and Organization Creation with Owner Memberships")

        # 2. Integrations for Org A
        IntegrationConfig.objects.create(organization=org_a, provider="INSTAGRAM", is_active=True, credentials={"access_token": "ig_token"}, metadata={"destination_id": "ig_page_1"})
        IntegrationConfig.objects.create(organization=org_a, provider="WHATSAPP", is_active=True, credentials={"access_token": "wa_token"}, metadata={"destination_id": "phone_id_1"})

        # 3. Simulate Inbound Messaging for Org A
        print("Simulating Inbound Webhooks...")
        from apps.conversations.services import ConversationService
        
        msg_ig, created_ig = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_user_1",
            "external_message_id": "mid.ig.1",
            "text": "Hi IG",
            "username": "ig_user_1",
            "destination_id": "ig_page_1",
        }, organization=org_a)
        
        msg_wa, created_wa = ConversationService.store_inbound_message({
            "channel": "WHATSAPP",
            "external_user_id": "919999999999",
            "external_message_id": "mid.wa.1",
            "text": "Hi WA",
            "phone_number": "+919999999999",
            "destination_id": "phone_id_1",
        }, organization=org_a)

        if msg_ig and msg_wa:
            report["PASS"].append("Webhook Message Ingestion (IG + WA)")
        else:
            report["HIGH"].append("Webhook Message Ingestion Failed")

        # 4. Check unified Inbox for Org A
        print("Checking Unified Inbox...")
        inbox_resp = client_a.get("/api/v1/conversations/")
        if inbox_resp.status_code == 200 and inbox_resp.json()["count"] == 2:
            report["PASS"].append("Unified Inbox Listing (2 conversations found)")
        else:
            report["HIGH"].append(f"Unified Inbox Listing expected 2, got {inbox_resp.json().get('count') if inbox_resp.status_code == 200 else inbox_resp.status_code}")

        # 5. Website Lead Form
        print("Testing Website Form...")
        form_a = LeadForm.objects.create(organization=org_a, name="Main Form", is_active=True)
        
        client_anon = APIClient(HTTP_HOST="localhost")
        form_resp = client_anon.post(f"/api/v1/forms/{form_a.public_id}/submit/", {
            "name": "Web Lead",
            "email": "web@example.com",
            "phone": "+1234567890",
            "message": "Interested"
        })
        if form_resp.status_code == 201:
            report["PASS"].append("Website Form Submission")
        else:
            report["HIGH"].append(f"Website Form Submission Failed: {form_resp.data}")
            
        # Check Dashboard Analytics for Org A
        dash_resp = client_a.get("/api/v1/analytics/dashboard/")
        if dash_resp.status_code == 200:
            data = dash_resp.json()
            if data["leads"]["total_leads"] >= 1:
                report["PASS"].append("Dashboard Analytics KPIs")
            else:
                report["HIGH"].append(f"Dashboard KPIs inaccurate: {data}")
        else:
            report["FAIL"].append(f"Dashboard Endpoint Failed: {dash_resp.data}")

        # 6. Cross-Tenant Isolation Tests
        print("Running Cross-Tenant Isolation Verification...")
        # User B tries to read Org A's leads list
        b_leads = client_b.get("/api/v1/leads/")
        if b_leads.status_code == 200 and b_leads.json()["count"] == 0:
            report["PASS"].append("Cross-Tenant: List Leads Isolated (0 leads visible for Org B)")
        else:
            report["BLOCKER"].append("Cross-Tenant: Org B can see Org A leads")

        lead_a = Lead.objects.filter(organization=org_a).first()
        if lead_a:
            b_lead_detail = client_b.get(f"/api/v1/leads/{lead_a.id}/")
            if b_lead_detail.status_code == 404:
                report["PASS"].append("Cross-Tenant: Read Lead Detail Isolated (404 Not Found for Org B)")
            else:
                report["BLOCKER"].append(f"Cross-Tenant: Org B accessed Org A lead! Status: {b_lead_detail.status_code}")

        # User B tries to read Org A's conversation list
        b_conv = client_b.get("/api/v1/conversations/")
        if b_conv.status_code == 200 and b_conv.json()["count"] == 0:
            report["PASS"].append("Cross-Tenant: List Conversations Isolated (0 threads visible for Org B)")
        else:
            report["BLOCKER"].append("Cross-Tenant: Org B can see Org A conversations")
            
        conv_a = Conversation.objects.filter(organization=org_a).first()
        if conv_a:
            b_conv_detail = client_b.get(f"/api/v1/conversations/{conv_a.id}/")
            if b_conv_detail.status_code == 404:
                report["PASS"].append("Cross-Tenant: Read Conversation Detail Isolated (404 Not Found for Org B)")
            else:
                report["BLOCKER"].append(f"Cross-Tenant: Org B accessed Org A conversation! Status: {b_conv_detail.status_code}")

        # 7. Idempotency & Validation Failure Testing
        # Duplicate message
        msg_ig_dup, created_dup = ConversationService.store_inbound_message({
            "channel": "INSTAGRAM",
            "external_user_id": "ig_user_1",
            "external_message_id": "mid.ig.1",  # Same ID
            "text": "Hi IG",
            "username": "ig_user_1",
            "destination_id": "ig_page_1",
        }, organization=org_a)
        if not created_dup:
            report["PASS"].append("Duplicate Webhook Idempotency (Ignored duplicate)")
        else:
            report["HIGH"].append("Duplicate Webhook Created Multiple Messages")

        # Invalid public form
        form_resp_invalid = client_anon.post(f"/api/v1/forms/{form_a.public_id}/submit/", {
            "name": "",
            "phone": ""
        })
        if form_resp_invalid.status_code == 400:
            report["PASS"].append("Invalid Public Form Validation (Rejected with 400 Bad Request)")
        else:
            report["MEDIUM"].append("Invalid Public Form Not Handled Correctly")

    except Exception as e:
        import traceback
        report["BLOCKER"].append(f"Exception during test run: {str(e)}\n{traceback.format_exc()}")

    import json
    print("\n================ FINAL E2E RESULTS ================")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_e2e()
