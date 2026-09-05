"""
Conversation and Message domain models for Instagram and WhatsApp channels.
Stores normalized messages independently of lead creation.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel, SoftDeletableModel


class Conversation(CoreModel, SoftDeletableModel):
    """
    A communication thread between the Photo Studio and a Customer on a specific channel.
    """

    class Channel(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", _("Instagram")
        WHATSAPP = "WHATSAPP", _("WhatsApp")
        WEBSITE = "WEBSITE", _("Website")

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        ARCHIVED = "ARCHIVED", _("Archived")
        CLOSED = "CLOSED", _("Closed")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text=_("The organization this conversation belongs to"),
        null=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text=_("The customer participating in this conversation"),
    )
    lead = models.ForeignKey(
        "leads.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations_inbox",
        help_text=_("The sales lead associated with this conversation"),
    )
    assigned_user = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
        help_text=_("Staff member assigned to manage this conversation"),
    )
    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=Channel.choices,
        db_index=True,
    )
    external_thread_id = models.CharField(
        _("external thread id"),
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_("Platform-specific thread or conversation identifier if available"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    last_message_at = models.DateTimeField(
        _("last message at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Timestamp of the most recent message in this conversation"),
    )
    last_message_preview = models.CharField(
        _("last message preview"),
        max_length=255,
        blank=True,
        help_text=_("Snippet of the most recent message"),
    )
    unread_count = models.PositiveIntegerField(
        _("unread count"),
        default=0,
        db_index=True,
        help_text=_("Number of unread inbound messages for admin review"),
    )

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ["-last_message_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "channel"],
                name="unique_customer_channel_conversation",
            ),
        ]
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["-last_message_at"]),
            models.Index(fields=["customer", "-last_message_at"]),
            models.Index(fields=["status", "unread_count"]),
            models.Index(fields=["assigned_user", "status"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.customer} ({self.status})"

    def mark_read(self):
        """Mark all unread inbound messages as read and reset unread count to 0."""
        from django.db import transaction
        with transaction.atomic():
            conversation = Conversation.objects.select_for_update().get(pk=self.pk)
            conversation.messages.filter(direction="INBOUND", is_read=False).update(is_read=True)
            conversation.unread_count = 0
            conversation.save(update_fields=["unread_count", "updated_at"])
            self.unread_count = 0



class Message(CoreModel):
    """
    An individual normalized message within a conversation.
    Supports platform-wide idempotency via external_message_id.
    """

    class Direction(models.TextChoices):
        INBOUND = "INBOUND", _("Inbound")
        OUTBOUND = "OUTBOUND", _("Outbound")

    class MessageType(models.TextChoices):
        TEXT = "TEXT", _("Text")
        IMAGE = "IMAGE", _("Image")
        VIDEO = "VIDEO", _("Video")
        AUDIO = "AUDIO", _("Audio")
        DOCUMENT = "DOCUMENT", _("Document")
        OTHER = "OTHER", _("Other")

    class DeliveryStatus(models.TextChoices):
        QUEUED = "QUEUED", _("Queued")
        SENDING = "SENDING", _("Sending")
        PENDING = "PENDING", _("Pending")
        SENT = "SENT", _("Sent")
        DELIVERED = "DELIVERED", _("Delivered")
        READ = "READ", _("Read")
        FAILED = "FAILED", _("Failed")

    client_request_id = models.CharField(max_length=128, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text=_("The parent conversation thread"),
    )
    direction = models.CharField(
        _("direction"),
        max_length=10,
        choices=Direction.choices,
        db_index=True,
        help_text=_("Message flow direction"),
    )
    sender = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_messages",
        help_text=_("Staff member who sent the message (if OUTBOUND)"),
    )
    external_message_id = models.CharField(
        _("external message id"),
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_("Unique identifier from WhatsApp (wamid) or Instagram for deduplication"),
    )
    is_read = models.BooleanField(
        _("is read"),
        default=False,
        db_index=True,
        help_text=_("Tracks whether this specific message has been read by the admin"),
    )
    message_type = models.CharField(
        _("message type"),
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        db_index=True,
    )
    text = models.TextField(
        _("text content"),
        blank=True,
        help_text=_("Normalized text message content"),
    )
    attachment_metadata = models.JSONField(
        _("attachment metadata"),
        default=dict,
        blank=True,
        help_text=_("Structured metadata for media (URL, mime type, size, thumbnail)"),
    )
    provider_timestamp = models.DateTimeField(
        _("provider timestamp"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Message creation timestamp sent by Meta webhook"),
    )
    delivery_status = models.CharField(
        _("delivery status"),
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.DELIVERED,
        db_index=True,
    )
    raw_payload = models.JSONField(
        _("raw payload"),
        default=dict,
        blank=True,
        help_text=_("Original sanitized webhook payload for debugging/audit"),
    )

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "external_message_id"],
                condition=~models.Q(external_message_id=""),
                name="unique_conversation_external_message",
            ),
            models.UniqueConstraint(fields=["conversation", "client_request_id"], condition=~models.Q(client_request_id=""), name="unique_conversation_send_request"),
        ]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["direction", "created_at"]),
            models.Index(fields=["external_message_id"]),
            models.Index(fields=["conversation", "delivery_status"]),
        ]

    def __str__(self):
        snippet = (self.text[:30] + "...") if len(self.text) > 30 else self.text
        return f"[{self.get_direction_display()}] {snippet or self.get_message_type_display()}"


class MessageReceipt(CoreModel):
    """Delivery callbacks can arrive before the send response has been persisted."""
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    channel = models.CharField(max_length=20)
    external_message_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    provider_timestamp = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "channel", "external_message_id", "status"], name="unique_tenant_message_receipt")]
