"""
Views and Webhook endpoints for Meta Instagram and WhatsApp Cloud API messaging integrations.
"""
import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from apps.organizations.permissions import IsOrganizationMember, IsOrganizationAdmin
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.conversations.services import ConversationService
from apps.integrations.meta.common.exceptions import (
    SignatureVerificationError,
    WebhookVerificationError,
)
from apps.integrations.meta.common.verifier import MetaSignatureVerifier
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider
from apps.integrations.models import RawWebhookEvent
from apps.integrations.pipeline import InboundPipelineService
from apps.integrations.serializers import (
    OutboundMessageSerializer,
    WebhookResponseSerializer,
)
from apps.integrations.tasks import (
    process_instagram_webhook_event_task,
    process_whatsapp_webhook_event_task,
)

logger = logging.getLogger("apps.integrations.views")


class MetaWebhookBaseView(APIView):
    """
    Base Webhook endpoint for Meta Integrations (Instagram Direct and WhatsApp Cloud API).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    default_channel = None
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        """
        Meta Webhook Verification Challenge.
        """
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        try:
            verified_challenge = MetaSignatureVerifier.verify_challenge(
                mode=mode,
                verify_token=token,
                challenge=challenge,
            )
            return HttpResponse(verified_challenge, content_type="text/plain", status=200)
        except WebhookVerificationError as exc:
            logger.warning("%s webhook verification challenge failed: %s", self.default_channel, str(exc))
            return HttpResponse("Forbidden", content_type="text/plain", status=403)

    def post(self, request, *args, **kwargs):
        """
        Ingests incoming webhook payload with cryptographic verification and fast 200 OK ack.
        """
        raw_body = request.body
        signature_header = (
            request.headers.get("X-Hub-Signature-256")
            or request.META.get("HTTP_X_HUB_SIGNATURE_256")
        )

        try:
            from .connection_service import app_credentials
            provider = self.default_channel
            if not provider:
                try:
                    obj = json.loads(raw_body).get("object")
                    provider = "WHATSAPP" if obj == "whatsapp_business_account" else "INSTAGRAM"
                except (ValueError, AttributeError, UnicodeDecodeError):
                    provider = "INSTAGRAM"
            MetaSignatureVerifier.verify_signature(raw_body, signature_header, app_secret=app_credentials(provider)[1])
        except SignatureVerificationError as exc:
            logger.warning("%s webhook signature verification failed: %s", self.default_channel, str(exc))
            return Response(
                {"detail": "Signature verification failed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (ValueError, UnicodeDecodeError) as exc:
            logger.error("Malformed JSON payload in %s webhook: %s", self.default_channel, str(exc))
            return Response(
                {"detail": "Malformed JSON payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(payload, dict) or not isinstance(payload.get("entry", []), list):
            return Response({"detail": "Webhook payload must be an object with an entry array."}, status=400)
        if any(not isinstance(entry, dict) for entry in payload.get("entry", [])):
            return Response({"detail": "Invalid webhook entry."}, status=400)

        # Determine channel
        channel = self.default_channel
        if payload.get("object") == "whatsapp_business_account":
            channel = RawWebhookEvent.Channel.WHATSAPP
        elif payload.get("object") in ("instagram", "page"):
            channel = RawWebhookEvent.Channel.INSTAGRAM
        elif not channel:
            channel = RawWebhookEvent.Channel.INSTAGRAM

        headers_dict = {
            k: v for k, v in request.headers.items() if k.lower() in ("content-type", "x-hub-signature-256", "x-request-id")
        }
        event, is_new = InboundPipelineService.record_raw_event(
            channel=channel,
            raw_body=raw_body,
            signature_header=signature_header,
            payload=payload,
            headers=headers_dict,
        )

        if not is_new and event and event.status in [RawWebhookEvent.Status.PROCESSED, RawWebhookEvent.Status.DUPLICATE]:
            logger.info("Duplicate %s webhook event ignored: %s", channel, event.event_id)
            return Response(
                {
                    "success": True,
                    "status": "duplicate_ignored",
                    "event_id": str(event.id),
                    "notes": "Event was already processed.",
                },
                status=status.HTTP_200_OK,
            )

        # Asynchronous processing handoff
        try:
            is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
            task_func = (
                process_whatsapp_webhook_event_task
                if channel == RawWebhookEvent.Channel.WHATSAPP
                else process_instagram_webhook_event_task
            )
            if is_eager:
                task_func.apply(args=[str(event.id)])
            else:
                task_func.delay(str(event.id))
        except Exception:
            logger.warning("Webhook queue unavailable; durable event retained for retry.")
            return Response({"detail": "Webhook queue unavailable; retry delivery.", "event_id": str(event.pk)}, status=503)

        return Response(
            {
                "success": True,
                "status": "received",
                "event_id": str(event.id),
            },
            status=status.HTTP_200_OK,
        )


class InstagramWebhookView(MetaWebhookBaseView):
    """
    Dedicated Webhook endpoint for Meta Instagram Direct Messaging.
    URL: /api/v1/webhooks/meta/instagram/
    """
    default_channel = RawWebhookEvent.Channel.INSTAGRAM


class WhatsAppWebhookView(MetaWebhookBaseView):
    """
    Dedicated Webhook endpoint for Meta WhatsApp Cloud API.
    URL: /api/v1/webhooks/meta/whatsapp/
    """
    default_channel = RawWebhookEvent.Channel.WHATSAPP


class IsActiveAdminUser(permissions.BasePermission):
    """
    Allows access only to active admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            request.user.is_active
        )


class OutboundMessageDispatchView(APIView):
    """
    Admin-only endpoint to send outbound messages and booking links through Meta messaging providers.
    """

    from apps.organizations.permissions import IsOrganizationMember
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def post(self, request, *args, **kwargs):
        from apps.conversations.models import Conversation
        from apps.conversations.send_serializers import SendMessageSerializer
        from apps.conversations.outbound import queue_message
        from apps.conversations.serializers import MessageSerializer
        serializer = OutboundMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conv = Conversation.objects.filter(organization=request.organization, channel=data["channel"], customer__identities__external_user_id=data["recipient_id"], customer__identities__channel=data["channel"], is_deleted=False).first()
        if not conv:
            return Response({"detail": "Recipient conversation not found in this workspace."}, status=404)
        content = {k: v for k, v in data.items() if k in ("text", "media_url", "media_type", "caption", "template")}
        payload = SendMessageSerializer(data=content)
        payload.is_valid(raise_exception=True)
        message = queue_message(conv, dict(payload.validated_data), request.user, request.data.get("request_id", ""))
        return Response(MessageSerializer(message).data, status=202)


class IntegrationHealthView(APIView):
    """
    Returns the health status of external integrations (Instagram, WhatsApp) for the current organization.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        from apps.integrations.models import IntegrationConfig
        from apps.conversations.outbound import configuration_status
        result = {}
        for provider in ("INSTAGRAM", "WHATSAPP"):
            config = IntegrationConfig.objects.filter(organization=request.organization, provider=provider).first()
            state, detail = configuration_status(config)
            meta = config.metadata if config else {}
            result[provider.lower()] = {
                "platform": provider.lower(), "connection_status": state,
                "status": state.lower(),
                "diagnostic": detail, "webhook_status": "ACTIVE" if config and config.is_active and meta.get("webhook_subscribed") else "UNKNOWN",
                "requires_reconnect": state not in ("CONNECTED", "CONFIGURED_UNVERIFIED"),
                "last_event_time": meta.get("last_event_time"), "last_error": meta.get("last_error"),
                "last_successful_communication": meta.get("last_accepted_at"),
                "required_permissions": ["instagram_business_basic", "instagram_business_manage_messages"] if provider == "INSTAGRAM" else ["whatsapp_business_messaging", "whatsapp_business_management"],
                **{k: meta.get(k) for k in ("username", "name", "profile_picture_url", "display_phone_number", "connected_at", "verified_name", "last_verified_at", "last_checked_at")},
                "business_name": meta.get("name"),
            }
        from apps.leads.models import LeadForm
        result["website"] = {"status": "configured" if LeadForm.objects.filter(organization=request.organization, is_active=True).exists() else "not_configured"}
        return Response(result)


# Connection lifecycle views live separately from webhook ingestion.
from .connection_views import (
    InstagramOAuthStartView, InstagramOAuthCallbackView, InstagramDisconnectView,
    WhatsAppOAuthStartView, WhatsAppOAuthCallbackView, WhatsAppDisconnectView,
    WhatsAppCompleteView, IntegrationVerifyView,
)


class InstagramDeauthorizeView(APIView):
    """
    Handles Meta App Deauthorization callback (when user uninstalls app from Facebook).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        from apps.integrations.meta.common.verifier import MetaSignatureVerifier
        from apps.integrations.models import IntegrationConfig

        signed_request = request.data.get("signed_request")
        if not signed_request:
            return Response({"error": "Missing signed_request"}, status=status.HTTP_400_BAD_REQUEST)

        from .connection_service import app_credentials
        payload = MetaSignatureVerifier.verify_signed_request(signed_request, app_secret=app_credentials("INSTAGRAM")[1])
        if not payload:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = payload.get("user_id")
        # In a multi-tenant environment, we need to find which config has this account_id
        # Note: metadata is JSONField, we can query by metadata__account_id
        configs = IntegrationConfig.objects.filter(provider="INSTAGRAM", metadata__account_id=str(user_id))
        configs.update(is_active=False, credentials={})

        logger.info("Meta app deauthorization processed")
        return Response({"status": "success"})


class InstagramDataDeletionView(APIView):
    """
    Handles Meta Data Deletion Request callback.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        from apps.integrations.meta.common.verifier import MetaSignatureVerifier
        from apps.integrations.models import IntegrationConfig

        signed_request = request.data.get("signed_request")
        if not signed_request:
            return Response({"error": "Missing signed_request"}, status=status.HTTP_400_BAD_REQUEST)

        from .connection_service import app_credentials
        payload = MetaSignatureVerifier.verify_signed_request(signed_request, app_secret=app_credentials("INSTAGRAM")[1])
        if not payload:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = payload.get("user_id")

        from django.db import transaction
        from django.urls import reverse
        from apps.integrations.models import DataDeletionRequest
        from apps.integrations.deletion import enqueue_deletion
        with transaction.atomic():
            configs = IntegrationConfig.objects.select_for_update().filter(provider="INSTAGRAM", metadata__account_id=str(user_id))
            scopes = [{"organization": str(c.organization_id), "account": str(c.metadata.get("destination_id") or user_id)} for c in configs]
            receipt = DataDeletionRequest.objects.create(scopes=scopes)
            configs.delete()
            transaction.on_commit(lambda: enqueue_deletion(receipt.pk))
        return Response({"url": request.build_absolute_uri(reverse("api_v1:integrations:data-deletion-status", kwargs={"code": receipt.pk})), "confirmation_code": str(receipt.pk)})
