from django.db import models
from apps.core.models import CoreModel


class AutomationUsage(CoreModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    runs_started = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "period_start", "period_end"], name="unique_automation_usage_period")]


class Automation(CoreModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="automations")
    name = models.CharField(max_length=160)
    channel = models.CharField(max_length=20, choices=[("INSTAGRAM", "Instagram"), ("WHATSAPP", "WhatsApp")])
    trigger_type = models.CharField(max_length=24, choices=[("INCOMING", "Incoming message"), ("EXACT", "Exact keyword"), ("CONTAINS", "Contains keyword"), ("FIRST_INTERACTION", "First interaction"), ("NEW_LEAD", "New lead from a message"), ("NEW_CONVERSATION", "New conversation")])
    trigger_value = models.CharField(max_length=255, blank=True)
    conditions = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=False)
    priority = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["priority", "created_at"]
        indexes = [models.Index(fields=["organization", "channel", "enabled"])]


class AutomationAction(CoreModel):
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name="actions")
    action_type = models.CharField(max_length=24, choices=[("SEND_REPLY", "Send reply"), ("CREATE_LEAD", "Create lead"), ("CHANGE_STATUS", "Change status"), ("ADD_TAG", "Add tag"), ("ASSIGN", "Assign lead"), ("BOOKING_LINK", "Send booking link")])
    action_order = models.PositiveSmallIntegerField(default=0)
    configuration = models.JSONField(default=dict)

    class Meta:
        ordering = ["action_order"]
        constraints = [models.UniqueConstraint(fields=["automation", "action_order"], name="unique_automation_action_order")]


class AutomationExecution(CoreModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    automation = models.ForeignKey(Automation, null=True, on_delete=models.SET_NULL, related_name="executions")
    automation_name = models.CharField(max_length=160)
    trigger_message = models.ForeignKey("conversations.Message", on_delete=models.CASCADE, related_name="automation_executions")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE)
    lead = models.ForeignKey("leads.Lead", null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=24, default="RUNNING")
    result = models.JSONField(default=list)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["automation", "trigger_message"], name="unique_automation_trigger_execution")]
