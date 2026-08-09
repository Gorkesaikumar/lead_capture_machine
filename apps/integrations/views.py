"""
Views and Webhook endpoints for Meta Instagram and WhatsApp Cloud API messaging integrations.
"""
import json
import logging
from django.conf import settings
from django.http import HttpResponse
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
            MetaSignatureVerifier.verify_signature(raw_body, signature_header)
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

        # Determine channel
        channel = self.default_channel
        if payload.get("object") == "whatsapp_business_account":
            channel = RawWebhookEvent.Channel.WHATSAPP
        elif payload.get("object") in ("instagram", "page"):
            channel = RawWebhookEvent.Channel.INSTAGRAM
        elif not channel:
            channel = RawWebhookEvent.Channel.INSTAGRAM

        headers_dict = {
            k: v for k, v in request.headers.items() if k.lower() != "authorization"
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
        except Exception as exc:
            logger.warning("Celery dispatch unavailable (%s), falling back to synchronous execution.", str(exc))
            try:
                InboundPipelineService.process_raw_webhook_event(event)
                event.status = RawWebhookEvent.Status.PROCESSED
                event.save(update_fields=["status", "updated_at"])
            except Exception as sync_exc:
                logger.exception("Synchronous fallback processing failed: %s", str(sync_exc))

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

    permission_classes = [IsActiveAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = OutboundMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        channel = data["channel"]
        recipient_id = data["recipient_id"]
        text = data.get("text")
        media_url = data.get("media_url")
        media_type = data.get("media_type", "IMAGE")
        caption = data.get("caption")

        import uuid
        local_message_id = f"local_{uuid.uuid4().hex}"

        # Store outbound message in domain conversation history as SENDING
        try:
            from apps.customers.models import Customer
            customer = Customer.objects.filter(identities__channel=channel, identities__external_user_id=recipient_id).first()
            if customer:
                from apps.conversations.models import Conversation
                conv, _ = Conversation.objects.get_or_create(customer=customer, channel=channel)
                ConversationService.store_outbound_message(
                    conversation=conv,
                    text=text or caption or "",
                    external_message_id=local_message_id,
                    message_type=media_type if media_url else "TEXT",
                    attachment_metadata={"media_url": media_url} if media_url else {},
                    raw_payload={},
                )
                from apps.conversations.models import Message
                Message.objects.filter(external_message_id=local_message_id).update(delivery_status="SENDING")
        except Exception as exc:
            logger.warning("Failed to store outbound message history: %s", str(exc))

        # Dispatch async task
        from apps.integrations.tasks import (
            send_instagram_message_task,
            send_instagram_media_message_task,
            send_whatsapp_message_task,
        )
        try:
            if channel == "INSTAGRAM":
                if media_url:
                    send_instagram_media_message_task.delay(
                        recipient_id=recipient_id,
                        media_url=media_url,
                        media_type=media_type,
                        caption=caption,
                        local_message_id=local_message_id,
                    )
                else:
                    send_instagram_message_task.delay(
                        recipient_id=recipient_id,
                        text=text or "",
                        local_message_id=local_message_id,
                    )
            else:
                # Fallback to sync or async for whatsapp
                # For now, just async whatsapp if it's text (assuming whatsapp media not fully implemented in views yet)
                send_whatsapp_message_task.delay(
                    recipient_phone=recipient_id,
                    text=text or "",
                    local_message_id=local_message_id,
                )
        except Exception as exc:
            logger.error("Failed to dispatch async task: %s", str(exc))
            # Fallback to sync if celery is down? Or just return error?
            return Response(
                {"detail": "Messaging queue unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "success": True,
                "external_message_id": local_message_id,
                "channel": channel,
            },
            status=status.HTTP_200_OK,
        )

class IntegrationHealthView(APIView):
    """
    Returns the health status of external integrations (Instagram, WhatsApp).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.conf import settings
        from apps.integrations.models import RawWebhookEvent
        import json

        ig_token = getattr(settings, "INSTAGRAM_ACCESS_TOKEN", "")
        wa_token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        wa_phone = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        meta_secret = getattr(settings, "META_APP_SECRET", "")

        # Fetch Instagram Events
        ig_events = RawWebhookEvent.objects.filter(channel=RawWebhookEvent.Channel.INSTAGRAM)
        ig_last = ig_events.order_by("-created_at").first()
        ig_last_success = ig_events.filter(status=RawWebhookEvent.Status.PROCESSED).order_by("-processed_at").first()
        
        ig_events_received = ig_events.count()
        ig_test_events = 0
        ig_real_events = 0

        # Diagnostics loop
        for e in ig_events:
            payload_str = json.dumps(e.payload) if e.payload else ""
            if "random_mid" in payload_str or '"id": "12334"' in payload_str or e.event_id.startswith("hash_"):
                ig_test_events += 1
            else:
                ig_real_events += 1

        # Fetch WhatsApp Events
        wa_events = RawWebhookEvent.objects.filter(channel=RawWebhookEvent.Channel.WHATSAPP)
        wa_last = wa_events.order_by("-created_at").first()
        wa_last_success = wa_events.filter(status=RawWebhookEvent.Status.PROCESSED).order_by("-processed_at").first()

        wa_events_received = wa_events.count()
        wa_test_events = 0
        wa_real_events = 0

        for e in wa_events:
            payload_str = json.dumps(e.payload) if e.payload else ""
            if e.event_id.startswith("hash_") or "test" in payload_str.lower():
                wa_test_events += 1
            else:
                wa_real_events += 1

        ig_status = "CONNECTED" if (ig_token and meta_secret) else "DISCONNECTED"
        wa_status = "CONNECTED" if (wa_token and wa_phone and meta_secret) else "DISCONNECTED"

        return Response({
            "instagram": {
                "platform": "instagram",
                "connection_status": ig_status,
                "webhook_status": "ACTIVE" if ig_last else "UNKNOWN",
                "last_event_time": ig_last.created_at if ig_last else None,
                "last_successful_communication": ig_last_success.processed_at if ig_last_success else None,
                "requires_reconnect": ig_status == "DISCONNECTED",
                "last_event_id": ig_last.event_id if ig_last else None,
                "last_processing_result": ig_last.status if ig_last else None,
                "last_error": None, # Error is not stored on model yet
                "events_received_count": ig_events_received,
                "real_message_events_count": ig_real_events,
                "test_events_count": ig_test_events,
            },
            "whatsapp": {
                "platform": "whatsapp",
                "connection_status": wa_status,
                "webhook_status": "ACTIVE" if wa_last else "UNKNOWN",
                "last_event_time": wa_last.created_at if wa_last else None,
                "last_successful_communication": wa_last_success.processed_at if wa_last_success else None,
                "requires_reconnect": wa_status == "DISCONNECTED",
                "last_event_id": wa_last.event_id if wa_last else None,
                "last_processing_result": wa_last.status if wa_last else None,
                "last_error": None,
                "events_received_count": wa_events_received,
                "real_message_events_count": wa_real_events,
                "test_events_count": wa_test_events,
            }
        })


class InstagramOAuthStartView(APIView):
    """
    Generates the Meta Instagram Business Login URL and returns it to the client.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        import secrets
        from django.core.cache import cache
        from django.conf import settings
        from django.urls import reverse

        app_id = getattr(settings, "META_APP_ID", "")
        # Build absolute URI based on the request host (handles ngrok, localhost, and production)
        base_url = request.build_absolute_uri('/')[:-1]
        redirect_uri = f"{base_url}{reverse('api_v1:integrations:oauth-instagram-callback')}"
        
        state = secrets.token_urlsafe(32)
        cache.set(f"oauth_state_{state}", True, timeout=600) # Valid for 10 mins

        scope = "instagram_business_basic,instagram_business_manage_messages"
        
        auth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?enable_fb_login=0"
            f"&force_authentication=1"
            f"&client_id={app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&state={state}"
        )
        return Response({"url": auth_url})


class InstagramOAuthCallbackView(APIView):
    """
    Handles the OAuth callback from Meta, validates state, and exchanges code for access token.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        import requests
        import os
        import dotenv
        from django.core.cache import cache
        from django.conf import settings
        from django.shortcuts import redirect
        from django.urls import reverse

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        error_description = request.query_params.get("error_description")
        
        # Use frontend URL from settings, falling back safely
        frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        frontend_redirect_url = f"{frontend_base}/admin/integrations" 

        if error:
            logger.error("Meta OAuth Error: %s - %s", error, error_description)
            return redirect(f"{frontend_redirect_url}?error={error}")

        if not code or not state:
            return redirect(f"{frontend_redirect_url}?error=missing_parameters")

        # Validate state (CSRF protection)
        if not cache.get(f"oauth_state_{state}"):
            return redirect(f"{frontend_redirect_url}?error=invalid_state")
        
        # Invalidate state to prevent replay attacks
        cache.delete(f"oauth_state_{state}")

        app_id = getattr(settings, "META_APP_ID", "")
        app_secret = getattr(settings, "META_APP_SECRET", "")
        
        base_url = request.build_absolute_uri('/')[:-1]
        redirect_uri = f"{base_url}{reverse('api_v1:integrations:oauth-instagram-callback')}"

        # 1. Exchange code for short-lived token
        token_url = "https://api.instagram.com/oauth/access_token"
        response = requests.post(token_url, data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code
        })

        if response.status_code != 200:
            logger.error("Failed to exchange code: %s", response.text)
            return redirect(f"{frontend_redirect_url}?error=token_exchange_failed")

        data = response.json()
        short_lived_token = data.get("access_token")
        user_id = data.get("user_id")

        if not short_lived_token or not user_id:
            logger.error("Invalid token response: %s", data)
            return redirect(f"{frontend_redirect_url}?error=invalid_token_payload")

        # 2. Exchange short-lived token for long-lived token
        ll_url = "https://graph.instagram.com/access_token"
        ll_response = requests.get(ll_url, params={
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_lived_token
        })

        if ll_response.status_code == 200:
            ll_data = ll_response.json()
            final_token = ll_data.get("access_token", short_lived_token)
        else:
            logger.warning("Long-lived token exchange failed: %s", ll_response.text)
            final_token = short_lived_token

        # 3. Store the token and numeric user_id securely in .env
        env_path = os.path.join(settings.BASE_DIR, ".env")
        if os.path.exists(env_path):
            dotenv.set_key(env_path, "INSTAGRAM_ACCESS_TOKEN", final_token)
            dotenv.set_key(env_path, "INSTAGRAM_ACCOUNT_ID", str(user_id))
            
            # Update settings dynamically for the running process
            # In a production environment, the server would need a restart, 
            # but for this dev setup, we update it in memory.
            settings.INSTAGRAM_ACCESS_TOKEN = final_token
            settings.INSTAGRAM_ACCOUNT_ID = str(user_id)
            
        # 4. Subscribe the specific Instagram Professional account to the messages webhook
        sub_url = f"https://graph.instagram.com/v20.0/{user_id}/subscribed_apps"
        sub_response = requests.post(sub_url, data={
            "subscribed_fields": "messages",
            "access_token": final_token
        })

        if sub_response.status_code != 200:
            logger.error("Failed to subscribe webhook for user %s: %s", user_id, sub_response.text)
            return redirect(f"{frontend_redirect_url}?error=webhook_subscription_failed")
        
        return redirect(f"{frontend_redirect_url}?integration_success=instagram")


class InstagramDeauthorizeView(APIView):
    """
    Handles Meta App Deauthorization callback (when user uninstalls app from Facebook).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        import os
        import dotenv
        from django.conf import settings
        from apps.integrations.meta.common.verifier import MetaSignatureVerifier

        signed_request = request.data.get("signed_request")
        if not signed_request:
            return Response({"error": "Missing signed_request"}, status=status.HTTP_400_BAD_REQUEST)

        payload = MetaSignatureVerifier.verify_signed_request(signed_request)
        if not payload:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Clear integration credentials
        env_path = os.path.join(settings.BASE_DIR, ".env")
        if os.path.exists(env_path):
            dotenv.set_key(env_path, "INSTAGRAM_ACCESS_TOKEN", "")
            settings.INSTAGRAM_ACCESS_TOKEN = ""
            
        logger.info(f"Meta App deauthorized by user_id: {payload.get('user_id')}")
        return Response({"status": "success"})


class InstagramDataDeletionView(APIView):
    """
    Handles Meta Data Deletion Request callback.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        import os
        import dotenv
        from django.conf import settings
        from apps.integrations.meta.common.verifier import MetaSignatureVerifier

        signed_request = request.data.get("signed_request")
        if not signed_request:
            return Response({"error": "Missing signed_request"}, status=status.HTTP_400_BAD_REQUEST)

        payload = MetaSignatureVerifier.verify_signed_request(signed_request)
        if not payload:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = payload.get("user_id")

        # Clear integration credentials
        env_path = os.path.join(settings.BASE_DIR, ".env")
        if os.path.exists(env_path):
            dotenv.set_key(env_path, "INSTAGRAM_ACCESS_TOKEN", "")
            settings.INSTAGRAM_ACCESS_TOKEN = ""

        logger.info(f"Meta Data Deletion requested by user_id: {user_id}")
        
        # Meta expects a specific JSON response
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        confirmation_url = f"{frontend_url}/data-deletion-status?code={user_id}"

        return Response({
            "url": confirmation_url,
            "confirmation_code": str(user_id)
        })
