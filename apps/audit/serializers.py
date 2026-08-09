"""
Serializers for Read-Only Audit Log REST APIs.
"""
from rest_framework import serializers
from apps.accounts.models import User
from apps.audit.models import AuditEvent


class AuditActorSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight, safe serializer for the user/actor associated with an audit event.
    """

    class Meta:
        model = User
        fields = ("id", "email", "full_name")
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for forensic audit events.
    """

    actor = AuditActorSummarySerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor",
            "action",
            "action_display",
            "entity_type",
            "entity_id",
            "metadata",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
