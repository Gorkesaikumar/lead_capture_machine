from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from apps.accounts.models import User
from apps.leads.models import Lead, LeadActivity, LeadTrigger
from apps.leads.serializers import (
    LeadActivitySerializer,
    LeadAssignStaffSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    LeadStatusUpdateSerializer,
    LeadTriggerSerializer,
    SendLeadMessageSerializer,
    SendBookingLinkSerializer,
)
from apps.leads.services import LeadManagementService
from apps.core.realtime import broadcast_new_message, broadcast_lead_updated


class LeadViewSet(viewsets.ModelViewSet):
    """
    Admin endpoints for managing sales leads and tracking conversions.
    """

    permission_classes = [IsAuthenticated]
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
        queryset = (
            Lead.objects.filter(is_deleted=False)
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
        return LeadDetailSerializer

    def perform_destroy(self, instance):
        instance.soft_delete()

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
                staff_user = User.objects.get(id=staff_id, is_active=True)
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

        if not lead.conversation_id:
            return Response(
                {"conversation": None, "messages": []},
                status=status.HTTP_200_OK,
            )

        try:
            conversation = (
                Conversation.objects.select_related("customer")
                .prefetch_related("messages")
                .get(id=lead.conversation_id)
            )
        except Conversation.DoesNotExist:
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

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request, pk=None):
        """
        POST /api/v1/leads/{id}/messages/
        Sends an outbound Instagram DM to the lead's customer.
        Enforces the Meta 24-hour messaging window policy.
        """
        import logging
        logger = logging.getLogger("apps.leads")

        lead = self.get_object()
        serializer = SendLeadMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message_text = serializer.validated_data["message"]

        # 1. Ensure this lead has Instagram as its source channel
        if lead.source_channel != "INSTAGRAM":
            return Response(
                {"error_code": "wrong_channel", "message": "This lead is not from Instagram."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Look up the customer's Instagram identity (IGSID)
        from apps.customers.models import CustomerIdentity
        from apps.integrations.meta.instagram.provider import InstagramMessagingProvider

        identity = (
            CustomerIdentity.objects.filter(
                customer=lead.customer,
                channel="INSTAGRAM",
            )
            .order_by("-updated_at")
            .first()
        )
        if not identity or not identity.external_user_id or not identity.external_user_id.strip():
            return Response(
                {
                    "error_code": "no_instagram_identity",
                    "message": (
                        "No Instagram identity found for this customer. "
                        "The customer must send an Instagram message to the studio first before you can reply."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        igsid = identity.external_user_id.strip()

        # Validate recipient ID format before attempting dispatch
        is_valid_id, id_error = InstagramMessagingProvider.validate_recipient_id(igsid)
        if not is_valid_id:
            logger.warning(
                "Invalid Instagram recipient ID for lead %s (customer=%s, raw_id=%s): %s",
                lead.id,
                lead.customer_id,
                igsid,
                id_error,
            )
            return Response(
                {
                    "error_code": "invalid_recipient_id",
                    "message": id_error or "Invalid Instagram recipient ID. The customer must send a message first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Check Meta 24-hour messaging window
        from apps.conversations.services import ConversationService
        within_window = ConversationService.is_within_24h_window(
            channel="INSTAGRAM",
            external_user_id=igsid,
        )
        if not within_window:
            return Response(
                {
                    "error_code": "messaging_window_closed",
                    "message": (
                        "Instagram's 24-hour messaging window has expired. "
                        "The customer must send a message first before you can reply."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Send via Instagram Messaging API
        provider = InstagramMessagingProvider()
        result = provider.send_text_message(recipient_id=igsid, text=message_text)

        # 5. Ensure conversation exists
        from apps.conversations.models import Conversation, Message
        if lead.conversation_id:
            conversation = Conversation.objects.get(id=lead.conversation_id)
        else:
            conversation, _ = Conversation.objects.get_or_create(
                customer=lead.customer,
                channel="INSTAGRAM",
            )
            lead.conversation = conversation
            lead.save(update_fields=["conversation", "updated_at"])

        # 6. Store outbound message regardless of success
        stored_message = ConversationService.store_outbound_message(
            conversation=conversation,
            text=message_text,
            external_message_id=result.external_message_id or "",
            raw_payload=result.provider_response or {},
        )

        if not result.success:
            stored_message.delivery_status = Message.DeliveryStatus.FAILED
            stored_message.raw_payload = {"error": result.error_message}
            stored_message.save(update_fields=["delivery_status", "raw_payload"])

            broadcast_new_message(stored_message, conversation=conversation, lead_id=str(lead.id))

            logger.error(
                "Failed to send Instagram DM for lead %s to IGSID %s: %s",
                lead.id, igsid, result.error_message,
            )
            return Response(
                {
                    "error_code": "send_failed",
                    "message": result.error_message or "Failed to send message via Instagram.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


        # 6. Log lead activity
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.MESSAGE_ATTACHED,
            actor=request.user,
            message=stored_message,
            description=f"Outbound Instagram DM sent: {message_text[:100]}",
            metadata={"external_message_id": result.external_message_id or ""},
        )

        # 7. Auto-advance lead status from NEW to CONTACTED
        if lead.status == Lead.Status.NEW:
            LeadManagementService.update_status(
                lead=lead,
                new_status=Lead.Status.CONTACTED,
                actor=request.user,
                notes="First outbound message sent via Instagram DM.",
            )

        # 8. Broadcast outbound message via WebSockets
        broadcast_new_message(stored_message, conversation=conversation, lead_id=str(lead.id))

        from apps.conversations.serializers import MessageSerializer
        return Response(
            MessageSerializer(stored_message).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="send-booking-link")
    def send_booking_link(self, request, pk=None):
        """
        POST /api/v1/leads/{id}/send-booking-link/
        Generates a secure booking link and sends it to the customer via Instagram DM.
        """
        import logging
        logger = logging.getLogger("apps.leads")

        lead = self.get_object()
        serializer = SendBookingLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        custom_message = serializer.validated_data.get("message", "")
        service_id = serializer.validated_data.get("service_id")

        # 1. Resolve optional service override
        service = lead.service
        if service_id:
            from apps.services.models import PhotographyService
            try:
                service = PhotographyService.objects.get(
                    id=service_id, is_deleted=False, is_active=True
                )
            except PhotographyService.DoesNotExist:
                return Response(
                    {"error_code": "invalid_service", "message": "Specified service not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 2. Look up Instagram identity
        from apps.customers.models import CustomerIdentity
        from apps.integrations.meta.instagram.provider import InstagramMessagingProvider

        identity = (
            CustomerIdentity.objects.filter(
                customer=lead.customer,
                channel="INSTAGRAM",
            )
            .order_by("-updated_at")
            .first()
        )
        if not identity or not identity.external_user_id or not identity.external_user_id.strip():
            return Response(
                {
                    "error_code": "no_instagram_identity",
                    "message": (
                        "No Instagram identity found for this customer. "
                        "The customer must send an Instagram message to the studio first before you can reply."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        igsid = identity.external_user_id.strip()

        # Validate recipient ID format
        is_valid_id, id_error = InstagramMessagingProvider.validate_recipient_id(igsid)
        if not is_valid_id:
            logger.warning(
                "Invalid Instagram recipient ID for lead %s (customer=%s, raw_id=%s): %s",
                lead.id,
                lead.customer_id,
                igsid,
                id_error,
            )
            return Response(
                {
                    "error_code": "invalid_recipient_id",
                    "message": id_error or "Invalid Instagram recipient ID. The customer must send a message first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Check 24-hour window
        from apps.conversations.services import ConversationService
        within_window = ConversationService.is_within_24h_window(
            channel="INSTAGRAM", external_user_id=igsid
        )
        if not within_window:
            return Response(
                {
                    "error_code": "messaging_window_closed",
                    "message": (
                        "Instagram's 24-hour messaging window has expired. "
                        "The customer must send a message first before you can reply."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Generate booking link
        from apps.bookings.services import BookingLinkService
        booking_link = BookingLinkService.create_for_lead(
            lead=lead,
            service=service,
            expires_in_days=7,
            created_by=request.user,
        )
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        booking_url = f"{frontend_url}/book/{booking_link.token}"

        # 5. Build final message text
        if custom_message:
            final_message = custom_message.replace("{BOOKING_URL}", booking_url)
        else:
            final_message = (
                f"Hi! 👋\n\n"
                f"Thank you for your interest. Here's your personalized booking link to select "
                f"your preferred date and time:\n\n"
                f"{booking_url}\n\n"
                f"We look forward to seeing you! 📸"
            )

        # 6. Send via Instagram
        from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
        provider = InstagramMessagingProvider()
        result = provider.send_text_message(recipient_id=igsid, text=final_message)

        # 7. Ensure conversation exists
        from apps.conversations.models import Conversation, Message
        if lead.conversation_id:
            conversation = Conversation.objects.get(id=lead.conversation_id)
        else:
            conversation, _ = Conversation.objects.get_or_create(
                customer=lead.customer, channel="INSTAGRAM"
            )
            lead.conversation = conversation
            lead.save(update_fields=["conversation", "updated_at"])

        # 8. Store outbound message regardless of success
        stored_message = ConversationService.store_outbound_message(
            conversation=conversation,
            text=final_message,
            external_message_id=result.external_message_id or "",
            raw_payload=result.provider_response or {},
        )

        if not result.success:
            stored_message.delivery_status = Message.DeliveryStatus.FAILED
            stored_message.raw_payload = {"error": result.error_message}
            stored_message.save(update_fields=["delivery_status", "raw_payload"])

            broadcast_new_message(stored_message, conversation=conversation, lead_id=str(lead.id))

            logger.error(
                "Failed to send booking link DM for lead %s to IGSID %s: %s",
                lead.id, igsid, result.error_message,
            )
            return Response(
                {
                    "error_code": "send_failed",
                    "message": result.error_message or "Failed to send booking link via Instagram.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


        # Note: BookingLinkService.create_for_lead already created the BOOKING_LINK_SENT
        # LeadActivity and updated lead status. We just attach the conversation message
        # to the most recent booking link activity so the conversation is linked.
        try:
            recent_activity = LeadActivity.objects.filter(
                lead=lead,
                activity_type=LeadActivity.ActivityType.BOOKING_LINK_SENT,
            ).latest("created_at")
            if not recent_activity.message:
                recent_activity.message = stored_message
                recent_activity.save(update_fields=["message", "updated_at"])
        except LeadActivity.DoesNotExist:
            pass

        # 8. Broadcast outbound message and lead update via WebSockets
        broadcast_new_message(stored_message, conversation=conversation, lead_id=str(lead.id))
        broadcast_lead_updated(lead)

        from apps.conversations.serializers import MessageSerializer
        return Response(
            {
                "message": MessageSerializer(stored_message).data,
                "booking_url": booking_url,
                "booking_link_token": booking_link.token,
            },
            status=status.HTTP_201_CREATED,
        )


class LeadTriggerViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for configuring automated intent detection keywords/phrases.
    """

    permission_classes = [IsAuthenticated]
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
