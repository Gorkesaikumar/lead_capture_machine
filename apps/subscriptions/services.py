"""
Subscription entitlement, multi-currency pricing, and lead quota enforcement services.
"""
import logging
from typing import Tuple, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.subscriptions.models import Plan, Subscription, UsageRecord, BillingTransaction, PaymentWebhookEvent
from apps.organizations.models import Organization

logger = logging.getLogger("apps.subscriptions")


from rest_framework.exceptions import APIException


class QuotaExceededException(APIException):
    status_code = 403
    default_code = "lead_limit_exceeded"
    """Raised when an organization attempts to capture a lead exceeding their plan quota."""
    pass


class CurrencyService:
    """
    Handles country detection, currency selection (INR for India, USD for International),
    and exact backend price calculation.
    """
    DEFAULT_CURRENCY = "USD"
    DEFAULT_COUNTRY = "US"

    COUNTRY_CURRENCY_MAP = {
        "IN": "INR",
        "US": "USD",
        "CA": "USD",
        "GB": "USD",
        "AU": "USD",
    }

    @classmethod
    def resolve_billing_country_and_currency(
        cls,
        requested_country: Optional[str] = None,
        organization: Optional[Organization] = None,
    ) -> Tuple[str, str]:
        """
        Priority:
        1. Explicitly requested country from client/checkout
        2. Existing organization subscription country
        3. Default fallback (IN for India / US for International)
        """
        country = (requested_country or "").strip().upper()
        if not country and organization and hasattr(organization, "subscription"):
            country = organization.subscription.billing_country

        if not country:
            country = "IN"  # Default primary market

        currency = cls.COUNTRY_CURRENCY_MAP.get(country, "USD")
        return country, currency

    @classmethod
    def get_plan_price(cls, plan: Plan, currency: str) -> Decimal:
        """
        Returns the exact backend-authoritative price for the given plan and currency.
        """
        if currency.upper() == "INR":
            return plan.price_inr
        return plan.price_usd


class SubscriptionEntitlementService:
    """
    Centralized entitlement engine managing subscription lifecycle, feature access,
    and concurrency-safe lead quota enforcement.
    """

    @classmethod
    def seed_default_plans(cls):
        """
        Seeds the 4 subscription plans: FREE ($0/₹0, 10 leads), STARTER ($5/₹400, 100 leads),
        CREATOR ($19/₹1500, 300 leads), ENTERPRISE ($99/₹8000, 1000 leads).
        """
        plans_data = [
            {
                "code": Plan.Code.FREE,
                "name": "Free",
                "description": "Try Nextora with real lead capture across all 3 channels",
                "price_usd": Decimal("0.00"),
                "price_inr": Decimal("0.00"),
                "lead_limit": 10,
                "display_order": 0,
                "can_use_instagram": True,
                "can_use_whatsapp": True,
                "can_use_website_forms": True,
                "can_use_automations": False,
                "automation_run_limit": 0,
                "can_access_analytics": True,
                "features": [
                    "10 leads / month combined",
                    "Instagram Direct DM capture",
                    "WhatsApp Business lead capture",
                    "Website Form embeds",
                    "Unified Sales Inbox",
                    "Standard lead management",
                ],
            },
            {
                "code": Plan.Code.STARTER,
                "name": "Starter",
                "description": "Essential lead capture for growing businesses",
                "price_usd": Decimal("5.00"),
                "price_inr": Decimal("400.00"),
                "lead_limit": 100,
                "display_order": 1,
                "can_use_instagram": True,
                "can_use_whatsapp": True,
                "can_use_website_forms": True,
                "can_use_automations": False,
                "automation_run_limit": 1000,
                "can_access_analytics": True,
                "features": [
                    "100 leads / month combined",
                    "Instagram Direct DM capture",
                    "WhatsApp Business lead capture",
                    "Website Form embeds",
                    "Unified Sales Inbox",
                    "Standard lead management",
                    "Optional DM Automation: +₹399/month",
                    "1,000 automation runs/month with add-on",
                ],
            },
            {
                "code": Plan.Code.CREATOR,
                "name": "Creator",
                "description": "Powerful automation & lead pipeline for growing teams",
                "price_usd": Decimal("19.00"),
                "price_inr": Decimal("1500.00"),
                "lead_limit": 300,
                "display_order": 2,
                "can_use_instagram": True,
                "can_use_whatsapp": True,
                "can_use_website_forms": True,
                "can_use_automations": True,
                "automation_run_limit": None,
                "can_access_analytics": True,
                "features": [
                    "300 leads / month combined",
                    "Everything in Starter",
                    "Advanced Lead Analytics",
                    "Automated Lead Triggers",
                    "DM Automation included (no add-on required)",
                    "Team Collaboration & Roles",
                    "Priority Inbox Routing",
                ],
            },
            {
                "code": Plan.Code.ENTERPRISE,
                "name": "Enterprise",
                "description": "High-volume lead generation with premium support",
                "price_usd": Decimal("99.00"),
                "price_inr": Decimal("8000.00"),
                "lead_limit": 1000,
                "display_order": 3,
                "can_use_instagram": True,
                "can_use_whatsapp": True,
                "can_use_website_forms": True,
                "can_use_automations": True,
                "automation_run_limit": None,
                "can_access_analytics": True,
                "features": [
                    "1,000 leads / month combined",
                    "Everything in Creator",
                    "DM Automation included (no add-on required)",
                    "Advanced Reporting & Exports",
                    "Multi-tenant Team Governance",
                    "Custom SLA & Priority Support",
                    "Dedicated Account Manager",
                ],
            },
        ]

        for p_data in plans_data:
            # Reading billing must never overwrite administrator-set prices or limits.
            Plan.objects.get_or_create(code=p_data["code"], defaults=p_data)

        # Migrate any legacy uppercase FREE plans and subscriptions
        canonical_free = Plan.objects.filter(code=Plan.Code.FREE).first()
        if canonical_free:
            legacy_plans = Plan.objects.filter(code__iexact="free").exclude(id=canonical_free.id)
            for leg in legacy_plans:
                Subscription.objects.filter(plan=leg).update(plan=canonical_free)
                leg.delete()

    @classmethod
    def get_or_create_active_subscription(cls, organization: Organization) -> Subscription:
        """
        Retrieves or provisions the active subscription for an organization.
        Default tier is FREE plan ($0, 10 leads limit).
        """
        cls.seed_default_plans()
        try:
            subscription = Subscription.objects.select_related("plan").get(organization=organization)
        except Subscription.DoesNotExist:
            free_plan = Plan.objects.get(code=Plan.Code.FREE)
            now = timezone.now()
            subscription = Subscription.objects.create(
                organization=organization,
                plan=free_plan,
                status=Subscription.Status.ACTIVE,
                billing_country="IN",
                billing_currency="INR",
                charged_amount=Decimal("0.00"),
                current_period_start=now,
                current_period_end=now + timezone.timedelta(days=30),
            )
        return subscription

    @classmethod
    def get_active_usage_record(cls, subscription: Subscription) -> UsageRecord:
        """
        Retrieves or creates the UsageRecord for the current billing period.
        Calculates total leads captured across Instagram, WhatsApp, and Website forms.
        """
        now = timezone.now()
        period_start = subscription.current_period_start or now
        period_end = subscription.current_period_end or (period_start + timezone.timedelta(days=30))

        usage, created = UsageRecord.objects.get_or_create(
            organization=subscription.organization,
            period_start=period_start,
            period_end=period_end,
            defaults={
                "subscription": subscription,
                "total_leads_count": 0,
                "instagram_lead_count": 0,
                "whatsapp_lead_count": 0,
                "website_lead_count": 0,
            },
        )

        if created:
            # Sync actual database lead count for the period from source of truth
            from apps.leads.models import Lead
            period_leads = Lead.objects.filter(
                organization=subscription.organization,
                created_at__gte=period_start,
                created_at__lte=period_end,
                is_deleted=False,
            )

            usage.total_leads_count = period_leads.count()
            usage.instagram_lead_count = period_leads.filter(source_channel__iexact="instagram").count()
            usage.whatsapp_lead_count = period_leads.filter(source_channel__iexact="whatsapp").count()
            usage.website_lead_count = period_leads.filter(source_channel__iexact="website").count()
            usage.save()

        return usage

    @classmethod
    def check_and_consume_lead_quota(cls, organization: Organization, channel: str) -> bool:
        """
        Atomic lead quota validation and reservation using DB row locks (`select_for_update`).
        
        Calculates:
            TOTAL LEADS = Instagram Leads + WhatsApp Leads + Website Leads
        
        If TOTAL LEADS >= Plan.lead_limit:
            Raises QuotaExceededException
        Else:
            Increments usage record atomically.
        """
        with transaction.atomic():
            Organization.objects.select_for_update().get(pk=organization.pk)
            # Lock Subscription & Organization row
            subscription = Subscription.objects.select_for_update().select_related("plan").filter(
                organization=organization
            ).first()

            if not subscription:
                cls.seed_default_plans()
                free_plan = Plan.objects.get(code=Plan.Code.FREE)
                now = timezone.now()
                subscription = Subscription.objects.create(
                    organization=organization,
                    plan=free_plan,
                    status=Subscription.Status.ACTIVE,
                    current_period_start=now,
                    current_period_end=now + timezone.timedelta(days=30),
                )

            if not subscription.is_valid:
                raise QuotaExceededException("Subscription is not active. Please renew your plan to continue capturing leads.")

            usage = UsageRecord.objects.select_for_update().filter(
                organization=organization,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
            ).first()

            if not usage:
                usage = cls.get_active_usage_record(subscription)

            # Combined quota enforcement
            current_total = usage.total_leads_count
            allowed_limit = subscription.plan.lead_limit

            if current_total >= allowed_limit:
                logger.warning(
                    "Lead quota exceeded for organization_id=%s plan=%s current=%d limit=%d",
                    organization.id, subscription.plan.code, current_total, allowed_limit
                )
                raise QuotaExceededException(
                    f"Monthly lead limit reached ({current_total}/{allowed_limit}). Upgrade your plan to continue capturing leads."
                )

            # Increment counter atomically
            usage.total_leads_count += 1
            ch = (channel or "").lower()
            if "insta" in ch:
                usage.instagram_lead_count += 1
            elif "whats" in ch:
                usage.whatsapp_lead_count += 1
            else:
                usage.website_lead_count += 1

            usage.save()
            return True
