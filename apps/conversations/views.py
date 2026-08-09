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


class ConversationViewSet(viewsets.ModelViewSet):
    """
    Admin endpoints for managing Instagram and WhatsApp conversations.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "channel",
        "status",
        "customer",
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
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        queryset = (
            Conversation.objects.filter(is_deleted=False)
            .select_related("customer")
            .prefetch_related("messages")
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
        messages_qs = conversation.messages.all().order_by("created_at")

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
