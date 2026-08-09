"""
Customer and CustomerIdentity models.
A Customer represents a real person who interacts with the photo studio.
Customers do NOT authenticate and do NOT inherit from User.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel, SoftDeletableModel


class Customer(CoreModel, SoftDeletableModel):
    """
    A real customer/client of the photo studio.
    Aggregates communication channels, leads, conversations, and bookings.
    """

    display_name = models.CharField(
        _("display name"),
        max_length=255,
        blank=True,
        help_text=_("Customer's preferred or known name"),
    )
    primary_phone = models.CharField(
        _("primary phone"),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Normalized primary contact phone number if known"),
    )
    email = models.EmailField(
        _("email address"),
        blank=True,
        db_index=True,
        help_text=_("Contact email address if known"),
    )
    notes = models.TextField(
        _("internal notes"),
        blank=True,
        help_text=_("Admin notes about client preferences, history, or special requests"),
    )
    first_seen_at = models.DateTimeField(
        _("first seen at"),
        default=timezone.now,
        db_index=True,
        help_text=_("Timestamp when the customer first interacted with the studio"),
    )
    last_seen_at = models.DateTimeField(
        _("last seen at"),
        default=timezone.now,
        db_index=True,
        help_text=_("Timestamp of the most recent interaction"),
    )

    class Meta:
        verbose_name = _("customer")
        verbose_name_plural = _("customers")
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["-last_seen_at"]),
            models.Index(fields=["display_name"]),
        ]

    def __str__(self):
        if self.display_name:
            return self.display_name
        if self.primary_phone:
            return f"Customer ({self.primary_phone})"
        if self.email:
            return f"Customer ({self.email})"
        return f"Customer ({self.id.hex[:8]})"

    @property
    def conversations_count(self) -> int:
        """Count of conversations linked to this customer."""
        if hasattr(self, "_conversations_count"):
            return self._conversations_count
        return getattr(self, "conversations", None).count() if hasattr(self, "conversations") else 0

    @property
    def leads_count(self) -> int:
        """Count of leads linked to this customer."""
        if hasattr(self, "_leads_count"):
            return self._leads_count
        return getattr(self, "leads", None).count() if hasattr(self, "leads") else 0

    @property
    def bookings_count(self) -> int:
        """Count of bookings linked to this customer."""
        if hasattr(self, "_bookings_count"):
            return self._bookings_count
        return getattr(self, "bookings", None).count() if hasattr(self, "bookings") else 0


class CustomerIdentity(CoreModel):
    """
    Represents an external communication identity on Instagram or WhatsApp.
    Ensures stable tracking even if usernames/handles change.
    """

    class Channel(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", _("Instagram")
        WHATSAPP = "WHATSAPP", _("WhatsApp")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="identities",
        help_text=_("The customer record this external identity maps to"),
    )
    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=Channel.choices,
        db_index=True,
        help_text=_("Communication channel platform"),
    )
    external_user_id = models.CharField(
        _("external user id"),
        max_length=255,
        db_index=True,
        help_text=_("Stable Meta ID: Instagram Scoped ID (IGSID) or WhatsApp ID (WAID)"),
    )
    username = models.CharField(
        _("username"),
        max_length=255,
        blank=True,
        help_text=_("External handle / display username if available (mutable)"),
    )
    normalized_phone = models.CharField(
        _("normalized phone"),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("E.164 normalized phone number where available"),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Platform-specific profile details or webhook payload context"),
    )

    class Meta:
        verbose_name = _("customer identity")
        verbose_name_plural = _("customer identities")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "external_user_id"],
                name="unique_channel_external_user_id",
            ),
        ]
        indexes = [
            models.Index(fields=["channel", "external_user_id"]),
            models.Index(fields=["channel", "username"]),
        ]

    def __str__(self):
        ident = self.username or self.external_user_id
        return f"[{self.get_channel_display()}] {ident}"
