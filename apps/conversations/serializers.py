"""
Serializers for Conversation and Message models.
"""
from rest_framework import serializers
from apps.conversations.models import Conversation, Message
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.accounts.models import User


class MessageSerializer(serializers.ModelSerializer):
    """
    Representation for an individual message.
    """

    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    message_type_display = serializers.CharField(source="get_message_type_display", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation_id",
            "direction",
            "direction_display",
            "external_message_id",
            "message_type",
            "message_type_display",
            "text",
            "attachment_metadata",
            "provider_timestamp",
            "delivery_status",
            "error_code",
            "error_message",
            "sender",
            "created_at",
        )
        read_only_fields = fields


class ConversationCustomerSerializer(serializers.ModelSerializer):
    """
    Lightweight customer summary attached to conversations.
    """

    class Meta:
        model = Customer
        fields = (
            "id",
            "display_name",
            "primary_phone",
            "email",
        )
        read_only_fields = fields


class ConversationLeadSerializer(serializers.ModelSerializer):
    """
    Lightweight lead summary attached to conversations.
    """
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    assigned_staff_name = serializers.CharField(source="assigned_staff.full_name", read_only=True, allow_null=True)

    class Meta:
        model = Lead
        fields = (
            "id",
            "status",
            "status_display",
            "tags",
            "source_channel",
            "assigned_staff_name",
        )
        read_only_fields = fields


class ConversationUserSerializer(serializers.ModelSerializer):
    """
    Lightweight user summary for assigned staff/sender.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
        )
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Summary representation of a conversation for list/inbox view.
    """

    customer = ConversationCustomerSerializer(read_only=True)
    lead = ConversationLeadSerializer(read_only=True)
    assigned_user = ConversationUserSerializer(read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "customer",
            "lead",
            "assigned_user",
            "channel",
            "channel_display",
            "status",
            "last_message_at",
            "last_message_preview",
            "unread_count",
            "created_at",
        )
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed representation of a conversation including recent message history.
    """

    customer = ConversationCustomerSerializer(read_only=True)
    lead = ConversationLeadSerializer(read_only=True)
    assigned_user = ConversationUserSerializer(read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    messages = serializers.SerializerMethodField()
    is_window_open = serializers.SerializerMethodField()

    def get_messages(self, obj):
        return MessageSerializer(list(obj.messages.order_by("-created_at")[:50])[::-1], many=True).data

    def get_is_window_open(self, obj):
        from .outbound import window_open
        return window_open(obj)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "customer",
            "lead",
            "assigned_user",
            "channel",
            "channel_display",
            "external_thread_id",
            "status",
            "last_message_at",
            "last_message_preview",
            "unread_count",
            "messages",
            "is_window_open",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
