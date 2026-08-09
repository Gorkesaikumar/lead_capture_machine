"""
Raw Webhook Event and Integration models.
Provides audit trails, fast ingestion storage, and idempotency guarantees for Meta webhooks.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel


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
