from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.db import transaction
from apps.accounts.models import User
from apps.leads.models import Lead, LeadActivity, LeadTrigger, LeadForm
from apps.leads.serializers import (
    LeadActivitySerializer,
    LeadAssignStaffSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    LeadStatusUpdateSerializer,
    LeadTriggerSerializer,
    SendLeadMessageSerializer,
    SendBookingLinkSerializer,
    LeadFormSerializer,
)
from apps.leads.services import LeadManagementService
from apps.core.realtime import broadcast_new_message, broadcast_lead_updated
from apps.core.mixins import TenantViewSetMixin


class LeadViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    """
    Admin endpoints for managing sales leads and tracking conversions.
    """

    from apps.organizations.permissions import IsOrganizationMember, IsOrganizationAdmin
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "status",
        "source_channel",
        "service",
        "assigned_staff",
    ]
    search_fields = [
        "customer__display_name",
        "customer__primary_phone",
        "customer__email",
        "summary",
        "notes",
    ]
    ordering_fields = [
        "created_at",
        "updated_at",
        "priority",
        "status",
    ]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(is_deleted=False)
            .select_related("customer", "service", "assigned_staff")
            .prefetch_related("activities", "activities__actor")
        )

        # Custom filter: source alias
        source_param = self.request.query_params.get("source")
        if source_param:
            queryset = queryset.filter(source_channel__iexact=source_param)

        # Custom filter: date
        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(created_at__date=date_param)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        if self.action == "create":
            from apps.leads.serializers import LeadCreateSerializer
            return LeadCreateSerializer
        return LeadDetailSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        selected_staff = serializer.validated_data.get("assigned_staff_id")
        staff = None
        if selected_staff:
            staff = User.objects.filter(pk=selected_staff, is_active=True, memberships__organization=request.organization, memberships__is_active=True).first()
            if not staff:
                return Response({"detail": "Assignee must be an active member of this workspace."}, status=400)
        lead = LeadManagementService.create_direct_lead(
            organization=request.organization,
            source_channel=serializer.validated_data["source_channel"],
            customer_name=serializer.validated_data["customer_name"],
            phone_number=serializer.validated_data.get("phone_number"),
            email=serializer.validated_data.get("email"),
            summary=serializer.validated_data.get("summary", ""),
            notes=serializer.validated_data.get("notes", ""),
            tags=serializer.validated_data.get("tags", []),
            source_identifier=serializer.validated_data.get("source_identifier", ""),
            actor=request.user
        )

        if "assigned_staff_id" in serializer.validated_data:
            LeadManagementService.assign_staff(lead, staff, actor=request.user)
        selected_status = serializer.validated_data.get("status")
        if selected_status and selected_status != lead.status:
            LeadManagementService.update_status(lead, selected_status, actor=request.user)

        return Response(
            LeadDetailSerializer(lead).data,
            status=status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance):
        instance.soft_delete()

    def perform_update(self, serializer):
        from django.db import transaction
        with transaction.atomic():
            serializer.instance = Lead.objects.select_for_update().get(pk=serializer.instance.pk)
            new_status = serializer.validated_data.pop("status", None)
            lead = serializer.save()
            if new_status and new_status != lead.status:
                LeadManagementService.update_status(lead, new_status, actor=self.request.user)
            from apps.core.realtime import broadcast_lead_updated
            transaction.on_commit(lambda: broadcast_lead_updated(lead))

    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request, pk=None):
        """
        POST /api/v1/leads/{id}/status/
        Updates lead status and logs an activity audit record.
        """
        lead = self.get_object()
        serializer = LeadStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        updated_lead = LeadManagementService.update_status(
            lead=lead,
            new_status=new_status,
            actor=request.user,
            notes=notes,
        )

        return Response(LeadDetailSerializer(updated_lead).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_staff(self, request, pk=None):
        """
        POST /api/v1/leads/{id}/assign/
        Assigns an admin/staff member to this lead.
        """
        lead = self.get_object()
        serializer = LeadAssignStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff_id = serializer.validated_data.get("staff_id")
        staff_user = None
        if staff_id:
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

        updated_lead = LeadManagementService.assign_staff(
            lead=lead,
            staff=staff_user,
            actor=request.user,
        )

        return Response(LeadDetailSerializer(updated_lead).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="activities")
    def activities(self, request, pk=None):
        """
        GET /api/v1/leads/{id}/activities/
        Returns full activity history for this lead.
        """
        lead = self.get_object()
        activities = lead.activities.select_related("actor").all().order_by("-created_at")
        serializer = LeadActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="conversation")
    def conversation(self, request, pk=None):
        """
        GET /api/v1/leads/{id}/conversation/
        Returns the linked conversation and its full message history (oldest-first).
        Marks conversation as read on fetch.
        """
        from apps.conversations.models import Conversation, Message
        from apps.conversations.serializers import ConversationDetailSerializer, MessageSerializer

        lead = self.get_object()

        try:
            conversation = (
                Conversation.objects.select_related("customer")
                .prefetch_related("messages")
                .filter(lead=lead)
                .order_by("-last_message_at")
                .first()
            )
            if not conversation:
                return Response(
                    {"conversation": None, "messages": []},
                    status=status.HTTP_200_OK,
                )
        except Exception:
            return Response(
                {"conversation": None, "messages": []},
                status=status.HTTP_200_OK,
            )

        # Mark as read when opened by admin
        from apps.conversations.services import ConversationService
        ConversationService.mark_conversation_as_read(conversation)

        # Check 24-hour messaging window status
        from datetime import timedelta
        from django.utils import timezone

        is_window_open = False
        window_expires_at = None
        last_inbound_message_at = None

        last_inbound = (
            conversation.messages.filter(direction=Message.Direction.INBOUND)
            .order_by("-provider_timestamp", "-created_at")
            .first()
        )
        if last_inbound:
            last_ts = last_inbound.provider_timestamp or last_inbound.created_at
            last_inbound_message_at = last_ts.isoformat()
            window_expires = last_ts + timedelta(hours=24)
            window_expires_at = window_expires.isoformat()
            is_window_open = timezone.now() < window_expires

        messages_qs = conversation.messages.all().order_by("created_at")
        messages_serializer = MessageSerializer(messages_qs, many=True)
        conversation_serializer = ConversationDetailSerializer(conversation)

        return Response(
            {
                "conversation": conversation_serializer.data,
                "messages": messages_serializer.data,
                "is_window_open": is_window_open,
                "window_expires_at": window_expires_at,
                "last_inbound_message_at": last_inbound_message_at,
            },
            status=status.HTTP_200_OK,
        )

    def _reply_conversation(self, lead):
        from apps.conversations.models import Conversation
        from rest_framework.exceptions import ValidationError
        conversation = Conversation.objects.filter(organization=lead.organization, customer=lead.customer, channel=lead.source_channel, is_deleted=False).first()
        if not conversation:
            raise ValidationError("A customer conversation is required before replying.")
        return conversation

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request, pk=None):
        from apps.conversations.outbound import queue_message, dispatch_message
        from apps.conversations.serializers import MessageSerializer
        lead = self.get_object()
        serializer = SendLeadMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = queue_message(self._reply_conversation(lead), {"text": serializer.validated_data["message"]}, request.user, request.data.get("request_id", ""), dispatch=False)
        message = dispatch_message(message.pk)
        if message.delivery_status not in ("SENT", "DELIVERED", "READ"):
            return Response({"error_code": message.error_code, "message": message.error_message, "record": MessageSerializer(message).data}, status=502)
        if lead.status == Lead.Status.NEW:
            LeadManagementService.update_status(lead, Lead.Status.CONTACTED, actor=request.user)
        return Response(MessageSerializer(message).data, status=201)

    @action(detail=True, methods=["post"], url_path="send-booking-link")
    def send_booking_link(self, request, pk=None):
        from apps.conversations.outbound import queue_message, dispatch_message, validate_send
        from apps.conversations.serializers import MessageSerializer
        from apps.bookings.services import BookingLinkService
        from apps.services.models import PhotographyService
        from django.shortcuts import get_object_or_404
        lead = self.get_object()
        serializer = SendBookingLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = self._reply_conversation(lead)
        validate_send(conversation, {"text": "Booking link"})
        service = lead.service
        if serializer.validated_data.get("service_id"):
            service = get_object_or_404(PhotographyService, pk=serializer.validated_data["service_id"], organization=request.organization, is_active=True, is_deleted=False)
        link = BookingLinkService.create_for_lead(lead=lead, service=service, expires_in_days=7, created_by=request.user)
        url = f"{settings.FRONTEND_URL}/book/{link.token}"
        custom = serializer.validated_data.get("message", "")
        text = custom.replace("{BOOKING_URL}", url) if custom else f"Choose a time for your appointment: {url}"
        if url not in text:
            text += f"\n{url}"
        message = queue_message(conversation, {"text": text}, request.user, dispatch=False)
        message = dispatch_message(message.pk)
        if message.delivery_status not in ("SENT", "DELIVERED", "READ"):
            return Response({"error_code": message.error_code, "message": message.error_message, "booking_url": url}, status=502)
        return Response({"message": MessageSerializer(message).data, "booking_url": url, "booking_link_token": link.token}, status=201)


class LeadTriggerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD endpoints for configuring automated intent detection keywords/phrases.
    """

    from apps.organizations.permissions import IsOrganizationAdmin
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    serializer_class = LeadTriggerSerializer
    queryset = LeadTrigger.objects.select_related("service").all().order_by("-created_at")
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active", "match_type", "priority", "service"]
    search_fields = ["phrase", "service__name"]
    ordering_fields = ["phrase", "priority", "created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]


class LeadFormViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD endpoints for configuring Lead Capture Forms.
    """

    from apps.organizations.permissions import IsOrganizationAdmin
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    serializer_class = LeadFormSerializer
    queryset = LeadForm.objects.all().order_by("-created_at")
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def perform_destroy(self, instance):
        instance.soft_delete()
