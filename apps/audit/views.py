from apps.organizations.permissions import IsOrganizationMember, IsOrganizationAdmin
"""
Read-Only REST API Views for Audit Logging.
Accessible only to authenticated Studio Administrators.
"""
from django_filters import rest_framework as django_filters
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer


class AuditEventFilter(django_filters.FilterSet):
    """
    FilterSet supporting action, entity_type, actor, and date ranges.
    """

    start_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    end_date = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    action = django_filters.CharFilter(field_name="action", lookup_expr="iexact")
    entity_type = django_filters.CharFilter(field_name="entity_type", lookup_expr="iexact")
    entity_id = django_filters.CharFilter(field_name="entity_id", lookup_expr="exact")
    actor = django_filters.UUIDFilter(field_name="actor__id")
    actor_email = django_filters.CharFilter(field_name="actor__email", lookup_expr="icontains")

    class Meta:
        model = AuditEvent
        fields = [
            "action",
            "entity_type",
            "entity_id",
            "actor",
            "actor_email",
            "start_date",
            "end_date",
        ]


class AuditEventReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Authorized read-only endpoint for reviewing administrative audit events.
    GET /api/v1/audit/
    GET /api/v1/audit/<uuid:id>/
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = AuditEventSerializer
    queryset = AuditEvent.objects.select_related("actor").all()
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AuditEventFilter
    search_fields = [
        "entity_id",
        "entity_type",
        "action",
        "actor__email",
        "actor__full_name",
        "ip_address",
    ]
    ordering_fields = ["created_at", "action", "entity_type"]
    ordering = ["-created_at"]
    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)

    http_method_names = ["get", "head", "options"]
