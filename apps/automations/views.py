from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.mixins import TenantViewSetMixin
from apps.organizations.permissions import IsOrganizationAdmin, IsOrganizationMember
from apps.leads.models import Lead
from .models import Automation, AutomationExecution
from .serializers import AutomationSerializer, ExecutionSerializer
from .services import matches


class AutomationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Automation.objects.prefetch_related("actions")
    serializer_class = AutomationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    filterset_fields = ["channel", "enabled"]
    search_fields = ["name"]

    @action(detail=True, methods=["post"], url_path="test")
    def test_rule(self, request, pk=None):
        automation = self.get_object()
        text = serializers.CharField(max_length=1000, allow_blank=True).run_validation(request.data.get("text", ""))
        first = serializers.BooleanField().run_validation(request.data.get("first_interaction", False))
        lead = None
        if request.data.get("lead_id"):
            lead_id = serializers.UUIDField().run_validation(request.data["lead_id"])
            lead = Lead.objects.filter(pk=lead_id, organization=request.organization, is_deleted=False).first()
            if not lead:
                raise serializers.ValidationError("Lead not found in this workspace.")
        new_lead = serializers.BooleanField().run_validation(request.data.get("new_lead", False))
        matched = matches(automation, text, first=first, lead=lead, new_lead=new_lead)
        return Response({"dry_run": True, "matched": matched, "enabled": automation.enabled, "actions": AutomationSerializer(automation).data["actions"] if matched else [], "note": "Preview only. No messages sent or records changed; live dispatch rechecks Meta configuration and messaging windows."})


class ExecutionViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AutomationExecution.objects.select_related("conversation")
    serializer_class = ExecutionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filterset_fields = ["automation", "status", "conversation"]
