from rest_framework import serializers
from apps.subscriptions.models import Plan, Subscription, UsageRecord, BillingTransaction
from apps.subscriptions.services import CurrencyService, SubscriptionEntitlementService

class PlanSerializer(serializers.ModelSerializer):
    automation_addon_available = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    is_popular = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "price_usd",
            "price_inr",
            "price",
            "currency",
            "currency_symbol",
            "billing_interval",
            "lead_limit",
            "max_users",
            "can_use_instagram",
            "can_use_whatsapp",
            "can_use_website_forms",
            "can_use_automations",
            "automation_run_limit", "automation_addon_available",
            "can_access_analytics",
            "features",
            "is_popular",
        ]

    def get_price(self, obj):
        if obj.code == Plan.Code.FREE:
            return "0"
        country = self.context.get("country", "IN")
        currency = self.context.get("currency", "INR")
        val = CurrencyService.get_plan_price(obj, currency)
        if val == int(val):
            return f"{int(val):,}"
        return f"{val:,.2f}"

    def get_automation_addon_available(self, obj):
        return obj.code == Plan.Code.STARTER

    def get_currency(self, obj):
        return self.context.get("currency", "INR")

    def get_currency_symbol(self, obj):
        curr = self.get_currency(obj)
        return "₹" if curr == "INR" else "$"

    def get_is_popular(self, obj):
        return obj.code == Plan.Code.CREATOR


class UsageRecordSerializer(serializers.ModelSerializer):
    leads_remaining = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UsageRecord
        fields = [
            "total_leads_count",
            "instagram_lead_count",
            "whatsapp_lead_count",
            "website_lead_count",
            "period_start",
            "period_end",
            "leads_remaining",
            "usage_percentage",
        ]

    def get_leads_remaining(self, obj):
        limit = obj.subscription.plan.lead_limit
        return max(0, limit - obj.total_leads_count)

    def get_usage_percentage(self, obj):
        limit = obj.subscription.plan.lead_limit
        if limit <= 0:
            return 0
        return min(100.0, round((obj.total_leads_count / limit) * 100, 1))


class SubscriptionSerializer(serializers.ModelSerializer):
    billing = serializers.SerializerMethodField()
    automation = serializers.SerializerMethodField()
    plan = PlanSerializer(read_only=True)
    usage = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "status",
            "billing_country",
            "billing_currency",
            "charged_amount",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "billing_provider",
            "plan",
            "usage",
            "is_valid",
            "automation",
            "billing",
        ]

    def get_usage(self, obj):
        usage_rec = SubscriptionEntitlementService.get_active_usage_record(obj)
        return UsageRecordSerializer(usage_rec).data

    def get_automation(self, obj):
        from apps.automations.usage import automation_access
        data = automation_access(obj)
        request = self.context.get("request")
        membership = getattr(request, "membership", None)
        data["can_manage_billing"] = bool(membership and membership.role in ("OWNER", "ADMIN"))
        return data

    def get_billing(self, obj):
        from django.conf import settings
        from .recurring import agreements
        from .payments import payment_available
        membership = getattr(self.context.get("request"), "membership", None)
        can_manage = bool(membership and membership.role in ("OWNER", "ADMIN"))
        result = {"test_mode": settings.RAZORPAY_KEY_ID.startswith("rzp_test_"),
            "payment_available": payment_available(), "cycles": settings.RAZORPAY_SUBSCRIPTION_CYCLES,
            "plan": None, "dm_automation": None}
        for product in ("plan", "dm_automation"):
            item = agreements(obj.organization).filter(product=product).order_by("-created_at").first()
            if item:
                result[product] = {"id": str(item.pk), "subscription_id": item.provider_id,
                    "status": item.status, "plan_code": item.plan.code, "amount": str(item.amount),
                    "currency": item.currency, "cancel_at_period_end": item.cancel_at_period_end,
                    "current_end": item.current_end, "short_url": item.short_url if can_manage else "",
                    "last_error": item.last_error, "paid_count": item.paid_count, "total_count": item.total_count}
        return result


class BillingTransactionSerializer(serializers.ModelSerializer):
    product_label = serializers.SerializerMethodField()

    def get_product_label(self, obj):
        if obj.payment_metadata.get("product") == "dm_automation":
            return "DM Automation add-on"
        code = obj.payment_metadata.get("plan_code")
        return f"{code.title()} plan" if code else "Subscription payment"
    class Meta:
        model = BillingTransaction
        fields = [
            "id",
            "product_label",
            "provider",
            "provider_payment_id",
            "provider_order_id",
            "amount",
            "currency",
            "status",
            "paid_at",
            "created_at",
        ]
