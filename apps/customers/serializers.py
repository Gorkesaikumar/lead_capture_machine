"""
Serializers for Customer management and profile representations.
"""
from rest_framework import serializers
from apps.customers.models import Customer, CustomerIdentity


class CustomerIdentitySerializer(serializers.ModelSerializer):
    """
    Safe external identity representation.
    """

    channel_display = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = CustomerIdentity
        fields = (
            "id",
            "channel",
            "channel_display",
            "external_user_id",
            "username",
            "normalized_phone",
            "created_at",
        )
        read_only_fields = fields


class CustomerListSerializer(serializers.ModelSerializer):
    """
    Representation for customer list / table view with communication identities and counts.
    """

    identities = CustomerIdentitySerializer(many=True, read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)
    leads_count = serializers.IntegerField(read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "display_name",
            "primary_phone",
            "email",
            "first_seen_at",
            "last_seen_at",
            "identities",
            "conversations_count",
            "leads_count",
            "bookings_count",
            "created_at",
        )
        read_only_fields = fields


class CustomerDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive representation for a Customer profile view.
    """

    identities = CustomerIdentitySerializer(many=True, read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)
    leads_count = serializers.IntegerField(read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "display_name",
            "primary_phone",
            "email",
            "notes",
            "first_seen_at",
            "last_seen_at",
            "identities",
            "conversations_count",
            "leads_count",
            "bookings_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "first_seen_at",
            "last_seen_at",
            "identities",
            "conversations_count",
            "leads_count",
            "bookings_count",
            "created_at",
            "updated_at",
        )


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for editing editable customer fields (notes, display name, contact info).
    """

    class Meta:
        model = Customer
        fields = (
            "display_name",
            "primary_phone",
            "email",
            "notes",
        )


class CustomerConversationsSummarySerializer(serializers.Serializer):
    """
    Conversations summary for a customer.
    """

    customer_id = serializers.UUIDField(source="id", read_only=True)
    total_conversations = serializers.IntegerField(source="conversations_count", read_only=True)
    recent_conversations = serializers.ListField(child=serializers.DictField(), default=list)


class CustomerLeadsSummarySerializer(serializers.Serializer):
    """
    Leads summary for a customer.
    """

    customer_id = serializers.UUIDField(source="id", read_only=True)
    total_leads = serializers.IntegerField(source="leads_count", read_only=True)
    recent_leads = serializers.ListField(child=serializers.DictField(), default=list)


class CustomerBookingsSummarySerializer(serializers.Serializer):
    """
    Bookings summary for a customer.
    """

    customer_id = serializers.UUIDField(source="id", read_only=True)
    total_bookings = serializers.IntegerField(source="bookings_count", read_only=True)
    recent_bookings = serializers.ListField(child=serializers.DictField(), default=list)
