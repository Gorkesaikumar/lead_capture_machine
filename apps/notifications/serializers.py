"""
DRF Serializers for Notification models.
"""
from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing notifications and delivery statuses.
    """
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "customer",
            "customer_name",
            "channel",
            "notification_type",
            "status",
            "idempotency_key",
            "context",
            "rendered_text",
            "external_message_id",
            "error_message",
            "is_permanent_error",
            "retry_count",
            "sent_at",
            "delivered_at",
            "read_at",
            "failed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class NotificationCreateSerializer(serializers.Serializer):
    """
    Serializer for ad-hoc admin notification dispatch.
    """
    customer_id = serializers.UUIDField(required=True)
    channel = serializers.ChoiceField(choices=Notification.Channel.choices, required=False)
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices,
        default=Notification.NotificationType.GENERAL,
    )
    context = serializers.DictField(required=False, default=dict)
    idempotency_key = serializers.CharField(required=False, max_length=255, allow_blank=True)
