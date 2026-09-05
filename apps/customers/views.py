"""
Customer API Views for Admin Dashboard.
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerBookingsSummarySerializer,
    CustomerConversationsSummarySerializer,
    CustomerDetailSerializer,
    CustomerLeadsSummarySerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
)


from apps.core.mixins import TenantViewSetMixin


class CustomerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    """
    CRUD and summary endpoints for Customer management (Admin only).
    """

    from apps.organizations.permissions import IsOrganizationMember
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "display_name",
        "primary_phone",
        "email",
        "identities__external_user_id",
        "identities__username",
    ]
    filterset_fields = [
        "identities__channel",
    ]
    ordering_fields = [
        "last_seen_at",
        "first_seen_at",
        "created_at",
        "display_name",
    ]
    ordering = ["-last_seen_at"]
    http_method_names = ["get", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        return (
            super().get_queryset().filter(is_deleted=False)
            .prefetch_related("identities")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerListSerializer
        elif self.action == "retrieve":
            return CustomerDetailSerializer
        elif self.action in ("update", "partial_update"):
            return CustomerUpdateSerializer
        return CustomerDetailSerializer

    def perform_destroy(self, instance):
        """Perform soft delete instead of permanent physical deletion."""
        instance.soft_delete()

    @action(detail=True, methods=["get"], url_path="conversations")
    def conversations(self, request, pk=None):
        """
        GET /api/v1/customers/{id}/conversations/
        Returns conversation history and summary metrics for this customer.
        """
        customer = self.get_object()
        # Fetch related conversations if conversation model is active
        recent_convs = []
        if hasattr(customer, "conversations"):
            for conv in customer.conversations.all()[:10]:
                recent_convs.append({
                    "id": str(conv.id),
                    "channel": getattr(conv, "channel", ""),
                    "status": getattr(conv, "status", ""),
                    "last_message_at": getattr(conv, "last_message_at", None),
                })

        serializer = CustomerConversationsSummarySerializer(
            customer,
            data={"recent_conversations": recent_convs},
        )
        serializer.is_valid()
        return Response({
            "status": "success",
            "data": {
                "customer_id": str(customer.id),
                "total_conversations": customer.conversations_count,
                "recent_conversations": recent_convs,
            },
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="leads")
    def leads(self, request, pk=None):
        """
        GET /api/v1/customers/{id}/leads/
        Returns lead history and summary metrics for this customer.
        """
        customer = self.get_object()
        recent_leads = []
        if hasattr(customer, "leads"):
            for lead in customer.leads.all()[:10]:
                recent_leads.append({
                    "id": str(lead.id),
                    "status": getattr(lead, "status", ""),
                    "service_requested": getattr(lead, "service_requested", ""),
                    "created_at": getattr(lead, "created_at", None),
                })

        return Response({
            "status": "success",
            "data": {
                "customer_id": str(customer.id),
                "total_leads": customer.leads_count,
                "recent_leads": recent_leads,
            },
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="bookings")
    def bookings(self, request, pk=None):
        """
        GET /api/v1/customers/{id}/bookings/
        Returns booking history and summary metrics for this customer.
        """
        customer = self.get_object()
        recent_bookings = []
        if hasattr(customer, "bookings"):
            for b in customer.bookings.all()[:10]:
                recent_bookings.append({
                    "id": str(b.id),
                    "status": getattr(b, "status", ""),
                    "start_time": getattr(b, "start_time", None),
                    "created_at": getattr(b, "created_at", None),
                })

        return Response({
            "status": "success",
            "data": {
                "customer_id": str(customer.id),
                "total_bookings": customer.bookings_count,
                "recent_bookings": recent_bookings,
            },
        }, status=status.HTTP_200_OK)
