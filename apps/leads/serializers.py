"""
Serializers for Leads, Triggers, and LeadActivity auditing.
"""
from rest_framework import serializers
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity, LeadTrigger
from apps.services.models import PhotographyService


class LeadTriggerSerializer(serializers.ModelSerializer):
    """
    Serializer for LeadTrigger CRUD.
    """

    match_type_display = serializers.CharField(source="get_match_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = LeadTrigger
        fields = (
            "id",
            "phrase",
            "match_type",
            "match_type_display",
            "service",
            "service_name",
            "priority",
            "priority_display",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LeadActivitySerializer(serializers.ModelSerializer):
    """
    Audit log serializer for LeadActivity events.
    """

    activity_type_display = serializers.CharField(source="get_activity_type_display", read_only=True)
    actor_email = serializers.CharField(source="actor.email", read_only=True)

    class Meta:
        model = LeadActivity
        fields = (
            "id",
            "activity_type",
            "activity_type_display",
            "actor_email",
            "description",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class LeadServiceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotographyService
        fields = ("id", "name", "slug", "base_price")
        read_only_fields = fields


class LeadCustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "display_name", "primary_phone", "email")
        read_only_fields = fields


class LeadStaffSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name")
        read_only_fields = fields


class LeadListSerializer(serializers.ModelSerializer):
    """
    Summary representation of a sales opportunity for table/pipeline board views.
    """

    customer = LeadCustomerSummarySerializer(read_only=True)
    service = LeadServiceSummarySerializer(read_only=True)
    assigned_staff = LeadStaffSummarySerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    trigger_phrase = serializers.CharField(source="trigger.phrase", read_only=True)
    trigger_service_name = serializers.CharField(source="trigger.service.name", read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id",
            "customer",
            "source_channel",
            "service",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "assigned_staff",
            "summary",
            "trigger_phrase",
            "trigger_service_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeadDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive representation of a Lead opportunity including activity history.
    """

    customer = LeadCustomerSummarySerializer(read_only=True)
    service = LeadServiceSummarySerializer(read_only=True)
    assigned_staff = LeadStaffSummarySerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    trigger_phrase = serializers.CharField(source="trigger.phrase", read_only=True)
    trigger_service_name = serializers.CharField(source="trigger.service.name", read_only=True)
    activities = LeadActivitySerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id",
            "customer",
            "source_channel",
            "conversation_id",
            "originating_message_id",
            "service",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "assigned_staff",
            "summary",
            "notes",
            "qualified_at",
            "closed_at",
            "trigger_phrase",
            "trigger_service_name",
            "activities",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer",
            "source_channel",
            "conversation_id",
            "originating_message_id",
            "qualified_at",
            "closed_at",
            "activities",
            "created_at",
            "updated_at",
        )


class LeadStatusUpdateSerializer(serializers.Serializer):
    """
    Payload for updating lead status.
    """

    status = serializers.ChoiceField(choices=Lead.Status.choices, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class LeadAssignStaffSerializer(serializers.Serializer):
    """
    Payload for assigning staff to a lead.
    """

    staff_id = serializers.UUIDField(required=False, allow_null=True)


class SendLeadMessageSerializer(serializers.Serializer):
    """
    Payload for sending an outbound Instagram DM from the CRM.
    """

    message = serializers.CharField(
        required=True,
        min_length=1,
        max_length=1000,
        error_messages={"required": "Message text is required.", "blank": "Message cannot be blank."},
    )


class SendBookingLinkSerializer(serializers.Serializer):
    """
    Payload for sending a booking link via Instagram DM.
    message: Optional custom text; use {BOOKING_URL} as a placeholder for the link.
    service_id: Optional service UUID to pre-select in the booking link.
    """

    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    service_id = serializers.UUIDField(required=False, allow_null=True)
