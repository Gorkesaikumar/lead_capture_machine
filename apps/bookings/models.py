"""
Booking and Booking Link domain models with PostgreSQL ExclusionConstraint.
Provides strict ACID scheduling guarantees and cryptographic booking links.
"""
from datetime import timedelta
import secrets
from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from psycopg.types.range import Range
from apps.core.models import CoreModel, SoftDeletableModel
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.services.models import Package, PhotographyService


def generate_booking_token() -> str:
    """Generates a cryptographically secure, URL-safe 43-character token."""
    return secrets.token_urlsafe(32)


class Booking(CoreModel, SoftDeletableModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, null=True)
    """
    Represents a customer appointment booking.
    Guarantees non-overlapping active appointments using PostgreSQL ExclusionConstraint.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")
        NO_SHOW = "NO_SHOW", _("No Show")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="bookings",
        help_text=_("Customer attending the photoshoot"),
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        help_text=_("Originating sales lead if converted from inbound inquiry"),
    )
    service = models.ForeignKey(
        PhotographyService,
        on_delete=models.PROTECT,
        related_name="bookings",
        help_text=_("The booked photography service"),
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        help_text=_("Optional specific package booked"),
    )
    starts_at = models.DateTimeField(
        _("starts at"),
        db_index=True,
        help_text=_("Scheduled session start time (timezone aware)"),
    )
    ends_at = models.DateTimeField(
        _("ends at"),
        db_index=True,
        help_text=_("Scheduled session end time (timezone aware)"),
    )
    buffer_before_minutes = models.PositiveIntegerField(
        _("buffer before (minutes)"),
        default=0,
        help_text=_("Preparation buffer before session start"),
    )
    buffer_after_minutes = models.PositiveIntegerField(
        _("buffer after (minutes)"),
        default=0,
        help_text=_("Cleanup buffer after session end"),
    )
    blocked_starts_at = models.DateTimeField(
        _("blocked starts at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Earliest studio lock timestamp including preparation buffer"),
    )
    blocked_ends_at = models.DateTimeField(
        _("blocked ends at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Latest studio lock timestamp including cleanup buffer"),
    )
    blocked_time_range = DateTimeRangeField(
        _("blocked time range"),
        null=True,
        blank=True,
        help_text=_("PostgreSQL GiST indexed range for physical exclusion constraints"),
    )
    status = models.CharField(
        _("booking status"),
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_index=True,
    )
    customer_notes = models.TextField(
        _("customer notes"),
        blank=True,
        help_text=_("Notes provided by the customer during booking"),
    )
    internal_notes = models.TextField(
        _("internal notes"),
        blank=True,
        help_text=_("Private studio notes or operational instructions"),
    )
    booked_at = models.DateTimeField(
        _("booked at"),
        default=timezone.now,
        help_text=_("Timestamp when the booking was finalized"),
    )
    cancelled_at = models.DateTimeField(
        _("cancelled at"),
        null=True,
        blank=True,
        help_text=_("Timestamp if the booking was cancelled"),
    )

    class Meta:
        verbose_name = _("booking")
        verbose_name_plural = _("bookings")
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["status", "starts_at", "ends_at"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["is_deleted"]),
        ]
        constraints = [
            ExclusionConstraint(
                name="exclude_tenant_overlapping_bookings",
                expressions=[
                    ("blocked_time_range", RangeOperators.OVERLAPS),
                    ("organization", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=["PENDING", "CONFIRMED"], is_deleted=False),
            )
        ]

    def __str__(self):
        return f"Booking #{str(self.id)[:8]} - {self.customer.display_name} ({self.service.name}) at {self.starts_at}"

    def save(self, *args, **kwargs):
        self.organization_id = self.customer.organization_id
        # Calculate blocked boundaries from session times and buffers
        if self.starts_at and self.ends_at:
            if not self.blocked_starts_at:
                self.blocked_starts_at = self.starts_at - timedelta(minutes=self.buffer_before_minutes)
            if not self.blocked_ends_at:
                self.blocked_ends_at = self.ends_at + timedelta(minutes=self.buffer_after_minutes)

            self.blocked_time_range = Range(
                self.blocked_starts_at, self.blocked_ends_at, bounds="[)"
            )

        super().save(*args, **kwargs)

    @property
    def duration_minutes(self) -> int:
        """Duration of actual session in minutes."""
        return int((self.ends_at - self.starts_at).total_seconds() // 60)


class BookingLink(CoreModel):
    """
    Secure, cryptographically random, one-time public booking link sent to leads.
    Allows customers to view studio availability and book without creating an account.
    """

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="booking_links",
        help_text=_("The sales lead this link was generated for"),
    )
    service = models.ForeignKey(
        PhotographyService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_links",
        help_text=_("Optional pre-selected photography service"),
    )
    token = models.CharField(
        _("secure token"),
        max_length=64,
        unique=True,
        db_index=True,
        default=generate_booking_token,
        help_text=_("Cryptographically secure URL-safe token"),
    )
    expires_at = models.DateTimeField(
        _("expires at"),
        db_index=True,
        help_text=_("Expiration timestamp after which the link cannot be used"),
    )
    is_used = models.BooleanField(
        _("is used"),
        default=False,
        db_index=True,
        help_text=_("Indicates whether this booking link was successfully redeemed"),
    )
    used_at = models.DateTimeField(_("used at"), null=True, blank=True)
    is_revoked = models.BooleanField(
        _("is revoked"),
        default=False,
        db_index=True,
        help_text=_("Manually revoked by studio admin"),
    )
    revoked_at = models.DateTimeField(_("revoked at"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_booking_links",
        help_text=_("Admin user who generated this link"),
    )

    class Meta:
        verbose_name = _("booking link")
        verbose_name_plural = _("booking links")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token", "is_used", "is_revoked"]),
            models.Index(fields=["lead", "-created_at"]),
        ]

    def __str__(self):
        return f"Booking Link for Lead #{str(self.lead.id)[:8]} (Expires: {self.expires_at})"

    @property
    def is_valid(self) -> bool:
        """Returns True if the link is active, unexpired, and not redeemed/revoked."""
        return (
            not self.is_used
            and not self.is_revoked
            and self.expires_at > timezone.now()
        )
