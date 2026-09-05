"""Authenticated connection commands and the public Instagram OAuth redirect."""
import logging
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from apps.organizations.permissions import IsOrganizationAdmin
from . import connection_service as service

logger = logging.getLogger("apps.integrations.connections")


class ConnectThrottle(UserRateThrottle):
    rate = "20/hour"
    scope = "meta_connect"


def failure_response(exc):
    return Response({"code": exc.code, "detail": service.ERRORS[exc.code]}, status=409)


class AdminConnectionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    throttle_classes = [ConnectThrottle]


class InstagramOAuthStartView(AdminConnectionView):
    def get(self, request):
        try:
            app_id, secret = service.app_credentials("INSTAGRAM")
            if not app_id or not secret or not settings.FRONTEND_URL:
                raise service.OAuthFailure("configuration_required")
            service.frontend_return_uri()
            callback = service.callback_uri(request, "INSTAGRAM")
            state = service.create_attempt(request.user, request.organization, "INSTAGRAM", callback)
            params = {"client_id": app_id, "redirect_uri": callback, "response_type": "code",
                      "scope": ",".join(service.SCOPES["INSTAGRAM"]), "state": state,
                      "enable_fb_login": "0", "force_authentication": "1"}
            return Response({"url": "https://www.instagram.com/oauth/authorize?"+urlencode(params)})
        except service.OAuthFailure as exc:
            return failure_response(exc)


class InstagramOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @method_decorator(sensitive_variables())
    def get(self, request):
        try:
            target = service.frontend_return_uri()
        except service.OAuthFailure as exc:
            return failure_response(exc)
        try:
            attempt = service.consume_attempt(request.query_params.get("state"), "INSTAGRAM")
            code = request.query_params.get("code")
            if request.query_params.get("error") or not code:
                raise service.OAuthFailure("authorization_cancelled")
            service.instagram_connect(attempt.organization, code, attempt.redirect_uri, attempt.user)
            query = {"integration_success": "instagram"}
        except service.OAuthFailure as exc:
            logger.warning("oauth_callback_failed", extra={"provider": "INSTAGRAM", "reason": exc.code})
            query = {"error": exc.code, "provider": "instagram"}
        except Exception:
            logger.error("oauth_callback_failed", extra={"provider": "INSTAGRAM", "reason": "internal_error"})
            query = {"error": "meta_connection_failed", "provider": "instagram"}
        response = redirect(target+"?"+urlencode(query))
        response["Referrer-Policy"] = "no-referrer"
        response["Cache-Control"] = "no-store"
        return response


class WhatsAppOAuthStartView(AdminConnectionView):
    def get(self, request):
        if not all([settings.META_APP_ID, settings.META_APP_SECRET, settings.META_WHATSAPP_CONFIG_ID]):
            return Response({"code": "configuration_required", "detail": "WhatsApp Embedded Signup is not configured. Ask your administrator to set the Meta app credentials and Embedded Signup configuration ID."}, status=409)
        return Response({"app_id": settings.META_APP_ID, "config_id": settings.META_WHATSAPP_CONFIG_ID,
            "graph_version": settings.META_GRAPH_API_VERSION,
            "state": service.create_attempt(request.user, request.organization, "WHATSAPP"),
            "expires_in": 600})


class CompleteSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=128, min_length=20)
    code = serializers.CharField(max_length=4096)
    waba_id = serializers.RegexField(r"^\d{1,32}$")
    phone_number_id = serializers.RegexField(r"^\d{1,32}$")


@method_decorator(sensitive_post_parameters("code", "state"), name="dispatch")
class WhatsAppCompleteView(AdminConnectionView):
    def post(self, request):
        serializer = CompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            attempt = service.consume_attempt(data["state"], "WHATSAPP", request.user, request.organization)
            service.whatsapp_connect(attempt, data["code"], data["waba_id"], data["phone_number_id"])
            return Response({"status": "connected", "provider": "whatsapp"})
        except service.OAuthFailure as exc:
            logger.warning("oauth_completion_failed", extra={"provider": "WHATSAPP", "reason": exc.code})
            return failure_response(exc)
        except Exception:
            logger.error("oauth_completion_failed", extra={"provider": "WHATSAPP", "reason": "internal_error"})
            return failure_response(service.OAuthFailure("meta_connection_failed"))


class WhatsAppOAuthCallbackView(WhatsAppCompleteView):
    """SDK onboarding completes by authenticated POST; legacy GET cannot create a connection."""
    def get(self, request):
        return Response({"detail": "Start WhatsApp Embedded Signup from Channels and complete it through the authenticated completion endpoint."}, status=405)


class InstagramDisconnectView(AdminConnectionView):
    provider = "INSTAGRAM"

    def post(self, request):
        service.disconnect(request.organization, self.provider)
        return Response({"success": True})


class WhatsAppDisconnectView(InstagramDisconnectView):
    provider = "WHATSAPP"


class IntegrationVerifyView(AdminConnectionView):
    def post(self, request, provider):
        from .health_service import verify_integration
        from .models import IntegrationConfig
        config = IntegrationConfig.objects.filter(organization=request.organization, provider=provider.upper(), is_active=True).first()
        if not config:
            return Response({"detail": "Connect this channel first."}, status=404)
        verify_integration(config.pk)
        return Response({"success": True})
