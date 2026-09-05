"""
Audit log models for tracking critical admin actions, domain mutations, and security events.
Guarantees append-only immutability.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditEventQuerySet(models.QuerySet):
    """
    Immutable QuerySet for AuditEvent preventing bulk updates and bulk deletions.
    """

    def update(self, **kwargs):
        raise PermissionError("AuditEvent records are append-only and cannot be modified.")

    def delete(self):
        raise PermissionError("AuditEvent records cannot be deleted.")


class AuditEventManager(models.Manager.from_queryset(AuditEventQuerySet)):
    """
    Manager for AuditEvent enforcing immutability.
    """
    pass


class AuditEvent(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, null=True)
    """
    Append-only forensic audit log for important administrative and domain actions.
    Records actor, action, affected entity, client IP, timestamp, and sanitized metadata.
    """

    class Action(models.TextChoices):
        LEAD_STATUS_CHANGED = "LEAD_STATUS_CHANGED", _("Lead Status Changed")
        LEAD_ASSIGNED = "LEAD_ASSIGNED", _("Lead Assigned")
        BOOKING_CREATED = "BOOKING_CREATED", _("Booking Created")
        BOOKING_CANCELLED = "BOOKING_CANCELLED", _("Booking Cancelled")
        AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED", _("Availability Changed")
        SERVICE_CHANGED = "SERVICE_CHANGED", _("Service Changed")
        BOOKING_LINK_GENERATED = "BOOKING_LINK_GENERATED", _("Booking Link Generated")
        BOOKING_LINK_SENT = "BOOKING_LINK_SENT", _("Booking Link Sent")
        INTEGRATION_SETTINGS_CHANGED = "INTEGRATION_SETTINGS_CHANGED", _("Integration Settings Changed")
        STAFF_ROLE_CHANGED = "STAFF_ROLE_CHANGED", _("Staff Role Changed")
        USER_LOGIN = "USER_LOGIN", _("User Login")
        USER_LOGOUT = "USER_LOGOUT", _("User Logout")
        CUSTOM = "CUSTOM", _("Custom Action")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier (UUIDv4)"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        help_text=_("User who performed the action (null for system/webhook actions)."),
    )
    action = models.CharField(
        _("action"),
        max_length=64,
        choices=Action.choices,
        db_index=True,
        help_text=_("Standardized audit action code."),
    )
    entity_type = models.CharField(
        _("entity type"),
        max_length=100,
        db_index=True,
        help_text=_("Class name of the affected domain entity (e.g. Lead, Booking)."),
    )
    entity_id = models.CharField(
        _("entity identifier"),
        max_length=255,
        db_index=True,
        blank=True,
        default="",
        help_text=_("Identifier of the affected entity (e.g. UUID, PK, or slug)."),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Sanitized context, diffs, or details about the event."),
    )
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
        help_text=_("Client IP address where available."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        db_index=True,
        help_text=_("Exact UTC timestamp when the audit event was recorded."),
    )

    objects = AuditEventManager()

    class Meta:
        db_table = "audit_events"
        verbose_name = _("audit event")
        verbose_name_plural = _("audit events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        """
        Enforce append-only immutability. Existing audit records can never be modified.
        """
        if not self._state.adding and self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise PermissionError("AuditEvent records are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Enforce append-only immutability. Audit records can never be deleted.
        """
        raise PermissionError("AuditEvent records cannot be deleted.")

    def __str__(self) -> str:
        actor_str = self.actor.email if self.actor else "System"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {actor_str} -> {self.action} ({self.entity_type}:{self.entity_id})"
