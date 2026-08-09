"""
Serializers for Conversation and Message models.
"""
from rest_framework import serializers
from apps.conversations.models import Conversation, Message
from apps.customers.models import Customer


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


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Summary representation of a conversation for list/inbox view.
    """

    customer = ConversationCustomerSerializer(read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "customer",
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
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "customer",
            "channel",
            "channel_display",
            "external_thread_id",
            "status",
            "last_message_at",
            "last_message_preview",
            "unread_count",
            "messages",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
