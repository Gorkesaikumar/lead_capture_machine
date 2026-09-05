from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, AdminAuditLog
from apps.organizations.models import Organization
from apps.subscriptions.models import Plan, Subscription, BillingTransaction
from apps.subscriptions.services import SubscriptionEntitlementService


class AdminPanelTestCase(TestCase):
    def setUp(self):
        SubscriptionEntitlementService.seed_default_plans()

        # Create Standard User (Non-admin)
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            full_name="Regular User",
            password="Password123!",
        )
        self.regular_org = Organization.objects.create(
            name="Regular Studio",
            slug="regular-studio",
            owner=self.regular_user,
        )
        SubscriptionEntitlementService.get_or_create_active_subscription(self.regular_org)

        # Create Super Admin User
        self.admin_user = User.objects.create_superuser(
            email="admin@nextora.com",
            full_name="Super Admin",
            password="SuperPassword123!",
        )

        self.client = APIClient()

    def test_permission_denied_for_regular_user(self):
        """Verify that standard users receive HTTP 403 Forbidden on admin endpoints."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/admin/kpis/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_granted_for_super_admin(self):
        """Verify super admin receives HTTP 200 OK on admin endpoints."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/kpis/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_users", response.data)
        self.assertIn("free_plan_users", response.data)

    def test_dynamic_plan_configuration_update(self):
        """Verify super admin can update USD/INR price and lead limits dynamically, creating an audit log."""
        self.client.force_authenticate(user=self.admin_user)
        starter = Plan.objects.get(code=Plan.Code.STARTER)

        payload = {
            "price_usd": "7.00",
            "price_inr": "550.00",
            "lead_limit": 150,
            "name": "Starter Plus",
        }
        response = self.client.patch(f"/api/v1/admin/subscriptions/plans/{starter.id}/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        starter.refresh_from_db()
        self.assertEqual(starter.price_usd, Decimal("7.00"))
        self.assertEqual(starter.price_inr, Decimal("550.00"))
        self.assertEqual(starter.lead_limit, 150)
        self.assertEqual(starter.name, "Starter Plus")

        # Verify audit log recorded
        audit = AdminAuditLog.objects.filter(action="update_plan_config").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.admin_email, self.admin_user.email)
        self.assertEqual(audit.target_name, "Starter Plus")

    def test_user_action_suspension_and_audit(self):
        """Verify super admin can suspend a user account and log audit history."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/admin/users/{self.regular_user.id}/action/",
            {"action": "suspend"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)

        audit = AdminAuditLog.objects.filter(action="user_suspend").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.target_id, str(self.regular_user.id))
