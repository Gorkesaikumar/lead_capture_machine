from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.subscriptions.models import Plan, Subscription, UsageRecord, BillingTransaction, PaymentWebhookEvent
from apps.subscriptions.services import (
    SubscriptionEntitlementService,
    CurrencyService,
    QuotaExceededException,
)
from apps.leads.models import Lead
from apps.customers.models import Customer


class SubscriptionAndQuotaTestCase(TestCase):
    def setUp(self):
        # Create test user and organization
        self.user = User.objects.create_user(
            email="owner@studio.com",
            full_name="Studio Owner",
            password="Password123!",
        )
        self.organization = Organization.objects.create(
            name="Nextora Test Studio",
            slug="nextora-test-studio",
            owner=self.user,
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )

        # Seed plans
        SubscriptionEntitlementService.seed_default_plans()

    def test_plan_seeding_and_pricing(self):
        """Test that all 4 plans (Free, Starter, Creator, Enterprise) are created with exact pricing and limits."""
        free = Plan.objects.get(code=Plan.Code.FREE)
        starter = Plan.objects.get(code=Plan.Code.STARTER)
        creator = Plan.objects.get(code=Plan.Code.CREATOR)
        enterprise = Plan.objects.get(code=Plan.Code.ENTERPRISE)

        self.assertEqual(free.lead_limit, 10)
        self.assertEqual(free.price_usd, Decimal("0.00"))
        self.assertEqual(free.price_inr, Decimal("0.00"))

        self.assertEqual(starter.lead_limit, 100)
        self.assertEqual(starter.price_usd, Decimal("5.00"))
        self.assertEqual(starter.price_inr, Decimal("400.00"))

        self.assertEqual(creator.lead_limit, 300)
        self.assertEqual(creator.price_usd, Decimal("19.00"))
        self.assertEqual(creator.price_inr, Decimal("1500.00"))

        self.assertEqual(enterprise.lead_limit, 1000)
        self.assertEqual(enterprise.price_usd, Decimal("99.00"))
        self.assertEqual(enterprise.price_inr, Decimal("8000.00"))

    def test_default_free_plan_assignment(self):
        """Test that new workspaces automatically receive the Free Plan with 10 lead credits."""
        subscription = SubscriptionEntitlementService.get_or_create_active_subscription(self.organization)
        self.assertEqual(subscription.plan.code, Plan.Code.FREE)
        self.assertEqual(subscription.plan.lead_limit, 10)
        self.assertTrue(subscription.is_valid)

    def test_free_plan_10_lead_quota_enforcement(self):
        """Test that 10th lead passes on Free Plan and 11th lead raises QuotaExceededException."""
        subscription = SubscriptionEntitlementService.get_or_create_active_subscription(self.organization)
        usage = SubscriptionEntitlementService.get_active_usage_record(subscription)
        usage.total_leads_count = 9
        usage.instagram_lead_count = 4
        usage.whatsapp_lead_count = 3
        usage.website_lead_count = 2
        usage.save()

        # 10th lead capture should succeed
        success = SubscriptionEntitlementService.check_and_consume_lead_quota(self.organization, "website")
        self.assertTrue(success)

        usage.refresh_from_db()
        self.assertEqual(usage.total_leads_count, 10)
        self.assertEqual(usage.website_lead_count, 3)

        # 11th lead capture MUST fail with QuotaExceededException
        with self.assertRaises(QuotaExceededException):
            SubscriptionEntitlementService.check_and_consume_lead_quota(self.organization, "instagram")

    def test_plan_upgrade_from_free_to_starter(self):
        """Test upgrading from Free Plan to Starter Plan expands limit from 10 to 100 while retaining usage."""
        subscription = SubscriptionEntitlementService.get_or_create_active_subscription(self.organization)
        usage = SubscriptionEntitlementService.get_active_usage_record(subscription)
        usage.total_leads_count = 10
        usage.save()

        # Upgrade plan to Starter
        starter_plan = Plan.objects.get(code=Plan.Code.STARTER)
        subscription.plan = starter_plan
        subscription.save()

        # Should now allow lead creation up to 100
        success = SubscriptionEntitlementService.check_and_consume_lead_quota(self.organization, "whatsapp")
        self.assertTrue(success)

        usage.refresh_from_db()
        self.assertEqual(usage.total_leads_count, 11)
        self.assertEqual(subscription.plan.lead_limit, 100)
