"""
Lead, LeadTrigger, and LeadActivity domain models.
Represents sales opportunities, configurable intent keywords, and audit logs.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel, SoftDeletableModel


class Lead(CoreModel, SoftDeletableModel):
    """
    A sales opportunity generated from customer inquiries.
    """

    class Status(models.TextChoices):
        NEW = "NEW", _("New")
        CONTACTED = "CONTACTED", _("Contacted")
        QUALIFIED = "QUALIFIED", _("Qualified")
        CONVERTED = "CONVERTED", _("Converted")
        LOST = "LOST", _("Lost")

    class Priority(models.TextChoices):
        LOW = "LOW", _("Low")
        MEDIUM = "MEDIUM", _("Medium")
        HIGH = "HIGH", _("High")
        URGENT = "URGENT", _("Urgent")

    ACTIVE_STATUSES = [
        Status.NEW,
        Status.CONTACTED,
        Status.QUALIFIED,
    ]

    TERMINAL_STATUSES = [
        Status.CONVERTED,
        Status.LOST,
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="leads",
        help_text=_("The organization this lead belongs to"),
        null=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="leads",
        help_text=_("The customer associated with this sales opportunity"),
    )
    source_channel = models.CharField(
        _("source channel"),
        max_length=20,
        choices=[
            ("INSTAGRAM", "Instagram"),
            ("WHATSAPP", "WhatsApp"),
            ("WEBSITE", "Website"),
            ("MANUAL", "Manual"),
        ],
        db_index=True,
    )
    source_identifier = models.CharField(
        _("source identifier"),
        max_length=255,
        blank=True,
        help_text=_("Optional tracking code, form ID, or external reference"),
    )
    tags = models.JSONField(
        _("tags"),
        default=list,
        blank=True,
        help_text=_("List of tags/labels applied to this lead"),
    )
    originating_message = models.ForeignKey(
        "conversations.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="originating_leads",
        help_text=_("The first message that triggered this lead opportunity"),
    )
    service = models.ForeignKey(
        "services.PhotographyService",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
        help_text=_("Photography service of interest (if identified)"),
    )
    trigger = models.ForeignKey(
        "LeadTrigger",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_leads",
        help_text="The trigger that automatically generated this lead, if any.",
    )
    status = models.CharField(
        _("status"),
        max_length=25,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    priority = models.CharField(
        _("priority"),
        max_length=15,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    assigned_staff = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
        help_text=_("Admin/Staff member assigned to manage this opportunity"),
    )
    summary = models.CharField(
        _("opportunity summary"),
        max_length=255,
        blank=True,
        help_text=_("Brief summary of customer inquiry"),
    )
    notes = models.TextField(
        _("notes"),
        blank=True,
        help_text=_("Internal sales notes, customer preferences, budget remarks"),
    )
    qualified_at = models.DateTimeField(
        _("qualified at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when lead was marked QUALIFIED"),
    )
    closed_at = models.DateTimeField(
        _("closed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when lead reached a terminal status"),
    )

    class Meta:
        verbose_name = _("lead")
        verbose_name_plural = _("leads")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["source_channel", "status"]),
            models.Index(fields=["priority", "status"]),
            models.Index(fields=["assigned_staff", "status"]),
            models.Index(fields=["is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(
                    status__in=["NEW", "CONTACTED", "QUALIFIED"],
                    is_deleted=False,
                ),
                name="unique_active_lead_per_customer",
            )
        ]

    def __str__(self):
        svc_name = self.service.name if self.service else "General Inquiry"
        return f"Lead #{self.id.hex[:8]} - {self.customer} ({svc_name}) [{self.get_status_display()}]"

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES


class LeadTrigger(CoreModel):
    """
    Configurable keywords and phrases for automated intent detection.
    """

    class MatchType(models.TextChoices):
        EXACT = "EXACT", _("Exact Match")
        CONTAINS = "CONTAINS", _("Contains Keyword/Phrase")
        REGEX = "REGEX", _("Regular Expression")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="lead_triggers",
        help_text=_("The organization this trigger belongs to"),
        null=True,
    )
    phrase = models.CharField(
        _("keyword / phrase"),
        max_length=255,
        db_index=True,
        help_text=_("The search phrase or pattern to detect in customer messages"),
    )
    match_type = models.CharField(
        _("match type"),
        max_length=20,
        choices=MatchType.choices,
        default=MatchType.CONTAINS,
        db_index=True,
    )
    service = models.ForeignKey(
        "services.PhotographyService",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="triggers",
        help_text=_("Optional service to map when this trigger matches"),
    )
    priority = models.CharField(
        _("priority"),
        max_length=15,
        choices=Lead.Priority.choices,
        default=Lead.Priority.MEDIUM,
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        db_index=True,
        help_text=_("Whether this trigger is active during message processing"),
    )

    class Meta:
        verbose_name = _("lead trigger")
        verbose_name_plural = _("lead triggers")
        ordering = ["-created_at"]

    def __str__(self):
        svc = f" -> {self.service.name}" if self.service else ""
        return f"[{self.get_match_type_display()}] \"{self.phrase}\"{svc}"


class LeadForm(CoreModel, SoftDeletableModel):
    """
    Configuration for public-facing lead capture forms (e.g. Website widgets).
    """

    import uuid

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="lead_forms",
        help_text=_("The organization this form belongs to"),
        null=True,
    )
    name = models.CharField(
        _("form name"),
        max_length=255,
        help_text=_("Internal name for this form (e.g., 'Main Website Contact')"),
    )
    public_id = models.UUIDField(
        _("public id"),
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        help_text=_("The public identifier used for form submission endpoints"),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        db_index=True,
        help_text=_("If disabled, public submissions to this form will be rejected"),
    )
    success_message = models.CharField(
        _("success message"),
        max_length=255,
        default="Thank you for your message. We will be in touch shortly.",
        help_text=_("Message to display to the user after successful submission"),
    )
    fields_config = models.JSONField(
        _("fields configuration"),
        default=dict,
        blank=True,
        help_text=_("Optional configuration for required fields or custom branding"),
    )

    class Meta:
        verbose_name = _("lead form")
        verbose_name_plural = _("lead forms")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.public_id})"


class LeadActivity(CoreModel):
    """
    Audit log of all state transitions and interactions on a Lead.
    """

    class ActivityType(models.TextChoices):
        LEAD_CREATED = "LEAD_CREATED", _("Lead Created")
        STATUS_CHANGED = "STATUS_CHANGED", _("Status Changed")
        STAFF_ASSIGNED = "STAFF_ASSIGNED", _("Staff Assigned")
        NOTE_ADDED = "NOTE_ADDED", _("Note Added")
        MESSAGE_ATTACHED = "MESSAGE_ATTACHED", _("Message Attached")

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text=_("The lead opportunity this activity belongs to"),
    )
    activity_type = models.CharField(
        _("activity type"),
        max_length=30,
        choices=ActivityType.choices,
        db_index=True,
    )
    actor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lead_activities",
        help_text=_("Admin user who performed the action (null if automated)"),
    )
    message = models.ForeignKey(
        "conversations.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lead_activities",
        help_text=_("Attached communication message if applicable"),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Human-readable log description"),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Contextual data (e.g. old_status, new_status, matched_trigger)"),
    )

    class Meta:
        verbose_name = _("lead activity")
        verbose_name_plural = _("lead activities")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_activity_type_display()}] on {self.lead} at {self.created_at}"
