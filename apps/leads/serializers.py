"""
Serializers for Leads, Triggers, and LeadActivity auditing.
"""
from rest_framework import serializers
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity, LeadTrigger, LeadForm
from apps.services.models import PhotographyService


class LeadFormSerializer(serializers.ModelSerializer):
    """
    Serializer for managing Lead Capture Forms.
    """
    submissions_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadForm
        fields = (
            "id",
            "name",
            "public_id",
            "is_active",
            "success_message",
            "fields_config",
            "submissions_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "submissions_count", "created_at", "updated_at")

    def get_submissions_count(self, obj):
        from apps.leads.models import Lead
        return Lead.objects.filter(
            source_channel="WEBSITE",
            source_identifier=str(obj.public_id),
            is_deleted=False
        ).count()


class PublicLeadSubmissionSerializer(serializers.Serializer):
    """
    Serializer for public website lead submission.
    """
    name = serializers.CharField(max_length=255, required=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    referrer = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    landing_page = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('phone') and not data.get('email'):
            raise serializers.ValidationError("Either phone or email is required.")
        return data


class LeadTriggerSerializer(serializers.ModelSerializer):
    def validate_service(self, value):
        request = self.context.get("request")
        if value and request and value.organization_id != request.organization.id:
            raise serializers.ValidationError("Service not found in this workspace.")
        return value

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
            "tags",
            "source_identifier",
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
    tags = serializers.ListField(child=serializers.CharField(max_length=80), max_length=50, required=False)

    class Meta:
        model = Lead
        fields = (
            "id",
            "customer",
            "source_channel",
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
            "tags",
            "source_identifier",
            "activities",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer",
            "source_channel",
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


class LeadCreateSerializer(serializers.Serializer):
    """
    Payload for creating a lead manually or via website form.
    """

    customer_name = serializers.CharField(max_length=255, required=True)
    status = serializers.ChoiceField(choices=Lead.Status.choices, required=False)
    assigned_staff_id = serializers.UUIDField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    source_channel = serializers.ChoiceField(
        choices=["MANUAL", "WEBSITE"], default="MANUAL"
    )
    summary = serializers.CharField(required=False, allow_blank=True, max_length=255)
    notes = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, default=list
    )
    source_identifier = serializers.CharField(required=False, allow_blank=True, max_length=255)
