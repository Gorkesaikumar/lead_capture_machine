"""
URL configuration for Integrations module.
"""
from django.urls import path
from .deletion import DataDeletionStatusView
from apps.integrations.views import (
    IntegrationHealthView,
    InstagramWebhookView,
    OutboundMessageDispatchView,
    WhatsAppWebhookView,
    InstagramOAuthStartView,
    InstagramOAuthCallbackView,
    InstagramDeauthorizeView,
    InstagramDataDeletionView,
    InstagramDisconnectView,
    WhatsAppOAuthStartView,
    WhatsAppOAuthCallbackView,
    WhatsAppDisconnectView,
    WhatsAppCompleteView,
    IntegrationVerifyView,
)

app_name = "integrations"

urlpatterns = [
    path("status/", IntegrationHealthView.as_view(), name="integration-status"),
    # Compatibility aliases. Register only oauth/instagram/callback/ with Meta.
    path("instagram/connect/", InstagramOAuthStartView.as_view(), name="instagram-connect"),
    path("instagram/callback/", InstagramOAuthCallbackView.as_view(), name="instagram-callback"),
    path("instagram/disconnect/", InstagramDisconnectView.as_view(), name="instagram-disconnect"),
    path("whatsapp/connect/", WhatsAppOAuthStartView.as_view(), name="whatsapp-connect"),
    path("whatsapp/complete/", WhatsAppCompleteView.as_view(), name="whatsapp-complete"),
    path("whatsapp/callback/", WhatsAppOAuthCallbackView.as_view(), name="whatsapp-callback"),
    path("whatsapp/disconnect/", WhatsAppDisconnectView.as_view(), name="whatsapp-disconnect"),
    path("<str:provider>/verify/", IntegrationVerifyView.as_view(), name="integration-verify"),
    path("data-deletion/<uuid:code>/", DataDeletionStatusView.as_view(), name="data-deletion-status"),
    # Meta webhook endpoints for Instagram Direct and WhatsApp Cloud API
    path("webhooks/meta/instagram/", InstagramWebhookView.as_view(), name="meta-instagram-webhook"),
    path("webhooks/meta/whatsapp/", WhatsAppWebhookView.as_view(), name="meta-whatsapp-webhook"),
    # Outbound messaging endpoint for studio admin
    path("messages/send/", OutboundMessageDispatchView.as_view(), name="outbound-send"),
    path("health/", IntegrationHealthView.as_view(), name="integration-health"),
    # Canonical Instagram Login endpoints used by the frontend and Meta dashboard.
    path("oauth/instagram/login/", InstagramOAuthStartView.as_view(), name="oauth-instagram-login"),
    path("oauth/instagram/callback/", InstagramOAuthCallbackView.as_view(), name="oauth-instagram-callback"),
    path("oauth/instagram/disconnect/", InstagramDisconnectView.as_view(), name="oauth-instagram-disconnect"),
    path("oauth/instagram/deauthorize/", InstagramDeauthorizeView.as_view(), name="oauth-instagram-deauthorize"),
    path("oauth/instagram/data-deletion/", InstagramDataDeletionView.as_view(), name="oauth-instagram-data-deletion"),
    # WhatsApp compatibility aliases; onboarding uses Embedded Signup + POST complete.
    path("oauth/whatsapp/login/", WhatsAppOAuthStartView.as_view(), name="oauth-whatsapp-login"),
    path("oauth/whatsapp/callback/", WhatsAppOAuthCallbackView.as_view(), name="oauth-whatsapp-callback"),
    path("oauth/whatsapp/disconnect/", WhatsAppDisconnectView.as_view(), name="oauth-whatsapp-disconnect"),
]
