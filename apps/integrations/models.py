"""
Raw Webhook Event and Integration models.
Provides audit trails, fast ingestion storage, and idempotency guarantees for Meta webhooks.
"""
from django.db import models
from django.conf import settings
from django.db.models.fields.json import KeyTextTransform
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel


class OAuthAttempt(CoreModel):
    """Short-lived, single-use authorization, bound to an initiating member."""
    state_hash = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=20)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    redirect_uri = models.URLField(max_length=1000, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)


class DataDeletionRequest(CoreModel):
    status = models.CharField(max_length=20, default="PENDING")
    scopes = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)


class IntegrationConfig(CoreModel):
    """
    Organization-specific integration configuration and credentials.
    Replaces global environment variables to allow multi-tenant Instagram/WhatsApp connections.
    """
    class Provider(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", _("Instagram")
        WHATSAPP = "WHATSAPP", _("WhatsApp")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="integration_configs",
    )
    provider = models.CharField(
        _("provider"),
        max_length=20,
        choices=Provider.choices,
        db_index=True,
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
    )
    credentials = models.JSONField(
        _("credentials"),
        default=dict,
        help_text=_("Encrypted or plain credentials (access tokens, phone IDs, etc)"),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Public metadata (e.g. connected page name)"),
    )

    class Meta:
        verbose_name = _("integration config")
        verbose_name_plural = _("integration configs")
        unique_together = [("organization", "provider")]
        constraints = [models.UniqueConstraint(
            models.F("provider"), KeyTextTransform("destination_id", "metadata"),
            condition=models.Q(is_active=True, metadata__has_key="destination_id") & ~models.Q(metadata__destination_id=""),
            name="unique_active_meta_destination",
        )]

    connected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.organization} - {self.get_provider_display()}"

    def get_credential(self, name):
        from apps.core.utils.crypto import decrypt_string
        return decrypt_string(self.credentials.get(name, ""))


class RawWebhookEvent(CoreModel):
    """
    Stores incoming raw webhook payloads for auditing, replayability, and strict idempotency.
    Webhooks are stored immediately and acknowledged before async processing begins.
    """

    class Channel(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", _("Instagram Direct")
        WHATSAPP = "WHATSAPP", _("WhatsApp Cloud API")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Async Processing")
        PROCESSING = "PROCESSING", _("Currently Processing")
        PROCESSED = "PROCESSED", _("Successfully Processed")
        DUPLICATE = "DUPLICATE", _("Duplicate Event Ignored")
        FAILED = "FAILED", _("Processing Failed")

    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=Channel.choices,
        db_index=True,
    )
    event_id = models.CharField(
        _("event identifier"),
        max_length=255,
        db_index=True,
        help_text=_("Unique identifier or hash of the webhook event for deduplication."),
    )
    signature = models.CharField(
        _("signature"),
        max_length=255,
        blank=True,
        help_text=_("HMAC signature header sent by Meta."),
    )
    headers = models.JSONField(
        _("request headers"),
        default=dict,
        blank=True,
    )
    payload = models.JSONField(
        _("raw payload"),
        help_text=_("Exact JSON body delivered by Meta webhook."),
    )
    status = models.CharField(
        _("processing status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    messages_count = models.PositiveIntegerField(
        _("messages count"),
        default=0,
        help_text=_("Number of customer messages extracted from this event."),
    )
    error_message = models.TextField(
        _("error message"),
        blank=True,
    )
    processed_at = models.DateTimeField(
        _("processed at"),
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "raw_webhook_events"
        verbose_name = _("raw webhook event")
        verbose_name_plural = _("raw webhook events")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "event_id"],
                name="unique_channel_webhook_event",
            )
        ]
        indexes = [
            models.Index(fields=["channel", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.channel}] {self.event_id} ({self.status})"
