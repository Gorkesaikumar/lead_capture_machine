from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.leads.models import LeadForm, LeadActivity
from apps.leads.serializers import PublicLeadSubmissionSerializer
from apps.leads.services import LeadManagementService
from apps.customers.models import Customer


class PublicLeadSubmissionThrottle(AnonRateThrottle):
    rate = '10/min'


class PublicLeadSubmissionView(APIView):
    """
    Public endpoint for submitting website leads.
    Expects a valid UUID `public_id` corresponding to a LeadForm.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicLeadSubmissionThrottle]

    def post(self, request, public_id):
        # The CORS signal allows only this public, write-only route for embeds.
        
        # 1. Fetch active LeadForm
        form = get_object_or_404(LeadForm, public_id=public_id, is_deleted=False, organization__is_active=True, organization__is_deleted=False)
        if not form.is_active:
            return Response(
                {"error": "This form is currently inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Validate incoming data
        serializer = PublicLeadSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        with transaction.atomic():
            # 3. Create or find customer (LeadManagementService.create_direct_lead handles this partially, 
            # but we need to pass notes and summary properly)
            
            # Combine message, referrer, landing_page into notes
            notes_parts = []
            if data.get("message"):
                notes_parts.append(f"Message: {data['message']}")
            if data.get("referrer"):
                notes_parts.append(f"Referrer: {data['referrer']}")
            if data.get("landing_page"):
                notes_parts.append(f"Landing Page: {data['landing_page']}")
                
            combined_notes = "\n\n".join(notes_parts)
            summary = (data.get("message") or "")[:255]
            if not summary:
                summary = f"Website inquiry from {data['name']}"

            # 4. Create Lead using service
            lead = LeadManagementService.create_direct_lead(
                organization=form.organization,
                source_channel="WEBSITE",
                customer_name=data["name"],
                phone_number=data.get("phone"),
                email=data.get("email"),
                summary=summary,
                notes=combined_notes,
                tags=["Website Lead"],
                source_identifier=str(form.public_id),
                actor=None  # System action
            )
            
            from apps.conversations.models import Conversation, Message
            from django.utils import timezone
            from django.db.models import F
            conversation, _ = Conversation.objects.get_or_create(customer=lead.customer, channel="WEBSITE", defaults={"organization": form.organization, "lead": lead})
            incoming = Message.objects.create(conversation=conversation, direction="INBOUND", text=data.get("message", ""), provider_timestamp=timezone.now())
            Conversation.objects.filter(pk=conversation.pk).update(unread_count=F("unread_count")+1, last_message_at=incoming.provider_timestamp, last_message_preview=incoming.text[:250])
            from apps.core.realtime import broadcast_new_message
            transaction.on_commit(lambda: broadcast_new_message(incoming))

            # 5. Log Activity
            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.NOTE_ADDED,
                description=f"Lead submitted via Website Form: {form.name}",
                metadata={
                    "form_id": str(form.id),
                    "referrer": data.get("referrer"),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")
                }
            )

        return Response(
            {
                "success": True,
                "message": form.success_message or "Successfully submitted."
            },
            status=status.HTTP_201_CREATED
        )
