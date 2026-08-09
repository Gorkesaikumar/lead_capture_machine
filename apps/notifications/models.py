"""
Notification models for tracking outbound communications across Meta channels.
"""
from django.db import models
from django.utils import timezone
from apps.core.models import CoreModel


class Notification(CoreModel):
    """
    Tracks lifecycle, delivery, and idempotency of an outbound notification request.
    """

    class Channel(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", "Instagram"
        WHATSAPP = "WHATSAPP", "WhatsApp"

    class NotificationType(models.TextChoices):
        BOOKING_LINK = "BOOKING_LINK", "Booking Link"
        BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION", "Booking Confirmation"
        BOOKING_REMINDER = "BOOKING_REMINDER", "Booking Reminder"
        BOOKING_CANCELLATION = "BOOKING_CANCELLATION", "Booking Cancellation"
        GENERAL = "GENERAL", "General Notification"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        READ = "READ", "Read"
        FAILED = "FAILED", "Failed"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="Target recipient customer",
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        help_text="Delivery channel (Instagram or WhatsApp)",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
        help_text="Functional domain purpose of the notification",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current delivery status",
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique key preventing duplicate outbound dispatches",
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dynamic parameters passed for template/copy formatting",
    )
    rendered_text = models.TextField(
        blank=True,
        help_text="Final rendered message body sent to recipient",
    )
    external_message_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Provider message ID (e.g. wamid or IG mid) for webhook correlation",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Diagnostic failure details if delivery failed",
    )
    is_permanent_error = models.BooleanField(
        default=False,
        help_text="If True, indicates unrecoverable failure and halts Celery retries",
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of attempted delivery retries",
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when provider accepted the message",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when message reached recipient device",
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when recipient opened the message",
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when message permanently or transiently failed",
    )

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["external_message_id"]),
        ]

    def __str__(self) -> str:
        return f"Notification {self.id} [{self.channel}:{self.notification_type}] -> {self.status}"

    def mark_sent(self, external_message_id: str):
        self.status = self.Status.SENT
        self.external_message_id = external_message_id
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "external_message_id", "sent_at", "updated_at"])

    def mark_delivered(self, delivered_at=None):
        self.status = self.Status.DELIVERED
        self.delivered_at = delivered_at or timezone.now()
        self.save(update_fields=["status", "delivered_at", "updated_at"])

    def mark_read(self, read_at=None):
        self.status = self.Status.READ
        self.read_at = read_at or timezone.now()
        self.save(update_fields=["status", "read_at", "updated_at"])

    def mark_failed(self, error_message: str, is_permanent: bool = False):
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.is_permanent_error = is_permanent
        self.failed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "error_message",
                "is_permanent_error",
                "retry_count",
                "failed_at",
                "updated_at",
            ]
        )
