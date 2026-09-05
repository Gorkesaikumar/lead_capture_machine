from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel
from apps.organizations.models import Organization

class Plan(CoreModel):
    """
    Defines a SaaS subscription tier (STARTER, CREATOR, ENTERPRISE)
    and the usage limits and entitlements associated with it.
    """
    class Code(models.TextChoices):
        FREE = "free", _("Free")
        STARTER = "starter", _("Starter")
        CREATOR = "creator", _("Creator")
        ENTERPRISE = "enterprise", _("Enterprise")

    code = models.CharField(
        _("plan code"),
        max_length=50,
        unique=True,
        choices=Code.choices,
        help_text=_("Internal unique identifier: free, starter, creator, enterprise"),
    )
    name = models.CharField(
        _("plan name"),
        max_length=100,
        help_text=_("Display name of the plan"),
    )
    description = models.TextField(
        _("description"),
        blank=True,
    )
    price_usd = models.DecimalField(
        _("monthly price USD"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    price_inr = models.DecimalField(
        _("monthly price INR"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    billing_interval = models.CharField(
        _("billing interval"),
        max_length=20,
        default="monthly",
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
    )
    display_order = models.IntegerField(
        _("display order"),
        default=0,
    )

    # Lead Quota (combined limit across Instagram, WhatsApp, Website)
    lead_limit = models.IntegerField(
        _("lead limit"),
        default=100,
        help_text=_("Combined lead limit per billing period across all channels"),
    )

    # Feature Entitlements
    max_users = models.IntegerField(
        _("max users"),
        null=True,
        blank=True,
        help_text=_("Maximum number of team members allowed (null = unlimited)"),
    )
    can_use_instagram = models.BooleanField(
        _("can use instagram"),
        default=True,
    )
    can_use_whatsapp = models.BooleanField(
        _("can use whatsapp"),
        default=True,
    )
    can_use_website_forms = models.BooleanField(
        _("can use website forms"),
        default=True,
    )
    can_use_automations = models.BooleanField(
        _("can use automations"),
        default=False,
    )
    automation_run_limit = models.PositiveIntegerField(null=True, blank=True, default=None,
        help_text="App runs per entitlement month; null means no app quota, not unlimited Meta sending.")
    can_access_analytics = models.BooleanField(
        _("can access analytics"),
        default=True,
    )

    features = models.JSONField(
        _("features list"),
        default=list,
        blank=True,
        help_text=_("List of bullet point features for UI display"),
    )

    class Meta:
        verbose_name = _("plan")
        verbose_name_plural = _("plans")
        ordering = ["display_order", "price_usd"]

    def __str__(self):
        return f"{self.name} ({self.code.upper()}) - {self.lead_limit} leads"


class Subscription(CoreModel):
    """
    Links an Organization to an active SaaS Subscription, tracking status, country, currency, and period.
    """
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past Due")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    billing_country = models.CharField(
        _("billing country"),
        max_length=2,
        default="IN",
        help_text=_("ISO 2-letter country code, e.g. IN, US"),
    )
    billing_currency = models.CharField(
        _("billing currency"),
        max_length=3,
        default="INR",
        help_text=_("Currency code, e.g. INR, USD"),
    )
    charged_amount = models.DecimalField(
        _("charged amount"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )

    # Billing cycle tracking
    current_period_start = models.DateTimeField(
        _("current period start"),
        default=timezone.now,
    )
    current_period_end = models.DateTimeField(
        _("current period end"),
        null=True,
        blank=True,
    )
    cancel_at_period_end = models.BooleanField(
        _("cancel at period end"),
        default=False,
    )
    automation_addon_start = models.DateTimeField(null=True, blank=True)
    automation_addon_end = models.DateTimeField(null=True, blank=True)

    # Payment Gateway Details
    billing_provider = models.CharField(
        _("billing provider"),
        max_length=50,
        default="razorpay",
        help_text=_("e.g. 'razorpay', 'stripe'"),
    )
    provider_customer_id = models.CharField(
        _("provider customer id"),
        max_length=255,
        blank=True,
    )
    provider_subscription_id = models.CharField(
        _("provider subscription id"),
        max_length=255,
        blank=True,
    )
    billing_account = models.CharField(max_length=64, blank=True)
    automation_billing_account = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.get_status_display()})"

    @property
    def is_valid(self):
        """Returns True if the subscription provides active service access."""
        from .payments import account_scope
        if self.billing_account and self.billing_account != account_scope():
            return False
        return self.status == self.Status.ACTIVE and (
            self.plan.code == Plan.Code.FREE or (
                self.current_period_start <= timezone.now()
                and (not self.current_period_end or self.current_period_end > timezone.now())
            )
        )

    @property
    def automation_entitled(self):
        from .payments import account_scope
        now = timezone.now()
        return bool(self.is_valid and (self.plan.can_use_automations or (
            self.plan.code == Plan.Code.STARTER and self.automation_addon_start
            and self.automation_addon_end and self.automation_addon_start <= now < self.automation_addon_end
            and (not self.automation_billing_account or self.automation_billing_account == account_scope())
        )))


class UsageRecord(CoreModel):
    """
    Tracks combined lead usage for an organization during a specific billing period.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    period_start = models.DateTimeField(
        _("period start"),
        db_index=True,
    )
    period_end = models.DateTimeField(
        _("period end"),
        db_index=True,
    )

    total_leads_count = models.IntegerField(
        _("total leads count"),
        default=0,
    )
    instagram_lead_count = models.IntegerField(
        _("instagram lead count"),
        default=0,
    )
    whatsapp_lead_count = models.IntegerField(
        _("whatsapp lead count"),
        default=0,
    )
    website_lead_count = models.IntegerField(
        _("website lead count"),
        default=0,
    )

    class Meta:
        verbose_name = _("usage record")
        verbose_name_plural = _("usage records")
        ordering = ["-period_start"]
        unique_together = ["organization", "period_start", "period_end"]

    def __str__(self):
        return f"{self.organization.name} ({self.total_leads_count} leads)"


class BillingTransaction(CoreModel):
    """
    Audit ledger of all subscription payments and orders.
    """
    class Status(models.TextChoices):
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        PENDING = "pending", _("Pending")
        REFUNDED = "refunded", _("Refunded")
        PARTIALLY_REFUNDED = "partially_refunded", _("Partially refunded")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="billing_transactions",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    provider = models.CharField(
        _("provider"),
        max_length=50,
        default="razorpay",
    )
    provider_payment_id = models.CharField(
        _("provider payment id"),
        max_length=255,
        blank=True,
    )
    provider_order_id = models.CharField(
        _("provider order id"),
        max_length=255,
        blank=True,
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="INR",
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_metadata = models.JSONField(
        _("payment metadata"),
        default=dict,
        blank=True,
    )
    paid_at = models.DateTimeField(
        _("paid at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("billing transaction")
        verbose_name_plural = _("billing transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization.name} - {self.currency} {self.amount} ({self.status})"


class PaymentWebhookEvent(CoreModel):
    """
    Stores incoming webhook payloads for strict signature verification and idempotency protection.
    """
    provider = models.CharField(
        _("provider"),
        max_length=50,
        default="razorpay",
    )
    event_id = models.CharField(
        _("event id"),
        max_length=255,
        unique=True,
        db_index=True,
    )
    event_type = models.CharField(
        _("event type"),
        max_length=100,
    )
    payload = models.JSONField(
        _("payload"),
        default=dict,
    )
    is_processed = models.BooleanField(
        _("is processed"),
        default=False,
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(
        _("processed at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("payment webhook event")
        verbose_name_plural = _("payment webhook events")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} - {self.event_id} ({self.event_type})"


class RecurringAgreement(CoreModel):
    """Immutable checkout price snapshot and the lifecycle of one Razorpay mandate."""
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="billing_agreements")
    product = models.CharField(max_length=30, choices=[("plan", "Plan"), ("dm_automation", "DM Automation")])
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    country = models.CharField(max_length=2)
    account_scope = models.CharField(max_length=64, db_index=True)
    provider_plan_id = models.CharField(max_length=80, blank=True)
    provider_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    status = models.CharField(max_length=30, default="creating")
    short_url = models.URLField(blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    current_start = models.DateTimeField(null=True, blank=True)
    current_end = models.DateTimeField(null=True, blank=True)
    paid_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=120)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    class Meta:
        indexes = [models.Index(fields=["organization", "product", "account_scope"])]


class RecurringCharge(CoreModel):
    """One paid invoice grants one provider-defined period, even under concurrent retries."""
    agreement = models.ForeignKey(RecurringAgreement, on_delete=models.PROTECT, related_name="charges")
    invoice_id = models.CharField(max_length=80, unique=True)
    payment_id = models.CharField(max_length=80, unique=True)
    transaction = models.OneToOneField(BillingTransaction, on_delete=models.PROTECT)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
