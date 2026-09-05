from django.db import transaction
from rest_framework import serializers
from apps.leads.models import Lead
from apps.organizations.models import OrganizationMembership
from .models import Automation, AutomationAction, AutomationExecution


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationAction
        fields = ["id", "action_type", "action_order", "configuration"]
        read_only_fields = ["id"]


class AutomationSerializer(serializers.ModelSerializer):
    actions = ActionSerializer(many=True)

    class Meta:
        model = Automation
        fields = ["id", "name", "channel", "trigger_type", "trigger_value", "conditions", "enabled", "priority", "actions", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        current = self.instance
        trigger = data.get("trigger_type", current.trigger_type if current else "")
        value = data.get("trigger_value", current.trigger_value if current else "")
        if trigger in ("EXACT", "CONTAINS") and not value.strip():
            raise serializers.ValidationError({"trigger_value": "A keyword is required."})
        conditions = data.get("conditions", current.conditions if current else {})
        if not isinstance(conditions, dict) or set(conditions)-{"lead_status", "has_tag", "message_type", "unassigned"}:
            raise serializers.ValidationError({"conditions": "Supported conditions: lead_status, has_tag, message_type, unassigned."})
        if "lead_status" in conditions and conditions["lead_status"] not in Lead.Status.values:
            raise serializers.ValidationError({"conditions": "Invalid lead status."})
        if "has_tag" in conditions and (not isinstance(conditions["has_tag"], str) or not 1 <= len(conditions["has_tag"]) <= 80):
            raise serializers.ValidationError({"conditions": "Tag must contain 1–80 characters."})
        if "message_type" in conditions and conditions["message_type"] not in ("TEXT", "IMAGE", "VIDEO", "AUDIO", "DOCUMENT", "OTHER"):
            raise serializers.ValidationError({"conditions": "Invalid message type."})
        if "unassigned" in conditions and not isinstance(conditions["unassigned"], bool):
            raise serializers.ValidationError({"conditions": "unassigned must be true or false."})
        org = self.context["request"].organization
        if data.get("enabled", current.enabled if current else False) and not org.has_feature("can_use_automations"):
            raise serializers.ValidationError({"enabled": "An active plan with DM Automation is required. You can save a disabled draft."})
        actions = data.get("actions")
        if actions is not None:
            if not 1 <= len(actions) <= 10 or len({a["action_order"] for a in actions}) != len(actions):
                raise serializers.ValidationError({"actions": "Use 1–10 actions with distinct order values."})
            for action in actions:
                config, kind = action["configuration"], action["action_type"]
                allowed = {"SEND_REPLY": {"text"}, "CREATE_LEAD": set(), "CHANGE_STATUS": {"status"}, "ADD_TAG": {"tag"}, "ASSIGN": {"user_id"}, "BOOKING_LINK": {"text"}}[kind]
                if not isinstance(config, dict) or set(config)-allowed:
                    raise serializers.ValidationError({"actions": f"Invalid configuration for {kind}."})
                if kind == "SEND_REPLY" and (not isinstance(config.get("text"), str) or not 1 <= len(config["text"].strip()) <= 1000):
                    raise serializers.ValidationError({"actions": "Reply requires 1–1000 characters."})
                if kind == "BOOKING_LINK" and "text" in config and (not isinstance(config["text"], str) or len(config["text"]) > 700):
                    raise serializers.ValidationError({"actions": "Booking introduction must be at most 700 characters."})
                if kind == "CHANGE_STATUS" and config.get("status") not in Lead.Status.values:
                    raise serializers.ValidationError({"actions": "Invalid lead status."})
                if kind == "ADD_TAG" and (not isinstance(config.get("tag"), str) or not 1 <= len(config["tag"].strip()) <= 80):
                    raise serializers.ValidationError({"actions": "Tag requires 1–80 characters."})
                if kind == "ASSIGN":
                    field = serializers.UUIDField()
                    user_id = field.run_validation(config.get("user_id"))
                    if not OrganizationMembership.objects.filter(organization=org, user_id=user_id, is_active=True, user__is_active=True).exists():
                        raise serializers.ValidationError({"actions": "Assignee must be an active workspace member."})
        return data

    @transaction.atomic
    def create(self, validated_data):
        actions = validated_data.pop("actions")
        instance = Automation.objects.create(**validated_data)
        for action in actions:
            AutomationAction.objects.create(automation=instance, **action)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        actions = validated_data.pop("actions", None)
        instance = super().update(instance, validated_data)
        if actions is not None:
            instance.actions.all().delete()
            for action in actions:
                AutomationAction.objects.create(automation=instance, **action)
        return instance


class ExecutionSerializer(serializers.ModelSerializer):
    delivery = serializers.SerializerMethodField()

    class Meta:
        model = AutomationExecution
        fields = ["id", "automation", "automation_name", "conversation", "lead", "trigger_message", "status", "result", "error", "delivery", "created_at"]
        read_only_fields = fields

    def get_delivery(self, obj):
        ids = [r["message_id"] for r in obj.result if r.get("message_id")]
        return list(obj.conversation.messages.filter(pk__in=ids).values("id", "delivery_status", "error_code", "error_message"))
