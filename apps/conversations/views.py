"""
API Views for Conversation management and message history.
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.conversations.models import Conversation, Message
from apps.conversations.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
)
from apps.conversations.services import ConversationService


from apps.core.mixins import TenantViewSetMixin


class ConversationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    """
    Admin endpoints for managing Instagram and WhatsApp conversations.
    """

    from apps.organizations.permissions import IsOrganizationMember
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "channel",
        "status",
        "customer",
        "assigned_user",
    ]
    search_fields = [
        "customer__display_name",
        "customer__primary_phone",
        "customer__email",
        "last_message_preview",
        "external_thread_id",
    ]
    ordering_fields = [
        "last_message_at",
        "unread_count",
        "created_at",
    ]
    ordering = ["-last_message_at"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Conversations are created from incoming channel messages or website forms."}, status=405)

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        from .send_serializers import SendMessageSerializer
        from .outbound import queue_message
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        request_id = payload.pop("request_id", "")
        message = queue_message(self.get_object(), payload, request.user, request_id)
        return Response(MessageSerializer(message).data, status=202)

    def get_queryset(self):
        queryset = (
            super().get_queryset().filter(is_deleted=False)
            .select_related("customer", "lead", "lead__assigned_staff", "assigned_user")
        )

        # Custom filter: unread only
        unread_param = self.request.query_params.get("unread")
        if unread_param and unread_param.lower() in ("true", "1", "yes"):
            queryset = queryset.filter(unread_count__gt=0)

        # Custom filter: date
        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(last_message_at__date=date_param)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ConversationListSerializer
        return ConversationDetailSerializer

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, pk=None):
        """
        GET /api/v1/conversations/{id}/messages/
        Returns paginated message history for this conversation.
        """
        conversation = self.get_object()
        messages_qs = conversation.messages.all().order_by("-created_at", "-id")

        page = self.paginate_queryset(messages_qs)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        """
        POST /api/v1/conversations/{id}/read/
        Marks the conversation as read by setting unread_count to 0.
        """
        conversation = self.get_object()
        ConversationService.mark_conversation_as_read(conversation)
        return Response(
            {
                "status": "success",
                "message": "Conversation marked as read.",
                "unread_count": 0,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request, pk=None):
        """
        POST /api/v1/conversations/{id}/status/
        Updates conversation status (e.g. ACTIVE, CLOSED).
        """
        conversation = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(Conversation.Status.choices):
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

        conversation.status = new_status
        conversation.save(update_fields=["status", "updated_at"])

        return Response(
            self.get_serializer(conversation).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_staff(self, request, pk=None):
        """
        POST /api/v1/conversations/{id}/assign/
        Assigns an admin/staff member to this conversation.
        """
        conversation = self.get_object()
        staff_id = request.data.get("staff_id")
        staff_user = None

        if staff_id:
            from apps.accounts.models import User
            try:
                staff_user = User.objects.filter(
                    id=staff_id,
                    is_active=True,
                    memberships__organization=request.organization, memberships__is_active=True
                ).distinct().get()
            except User.DoesNotExist:
                return Response(
                    {"detail": f"User with id {staff_id} not found or inactive."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        conversation.assigned_user = staff_user
        conversation.save(update_fields=["assigned_user", "updated_at"])

        return Response(
            self.get_serializer(conversation).data,
            status=status.HTTP_200_OK,
        )
