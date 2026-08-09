"""
URL configuration for Integrations module.
"""
from django.urls import path
from apps.integrations.views import (
    IntegrationHealthView,
    InstagramWebhookView,
    OutboundMessageDispatchView,
    WhatsAppWebhookView,
    InstagramOAuthStartView,
    InstagramOAuthCallbackView,
    InstagramDeauthorizeView,
    InstagramDataDeletionView,
)

app_name = "integrations"

urlpatterns = [
    # Meta webhook endpoints for Instagram Direct and WhatsApp Cloud API
    path("webhooks/meta/instagram/", InstagramWebhookView.as_view(), name="meta-instagram-webhook"),
    path("webhooks/meta/whatsapp/", WhatsAppWebhookView.as_view(), name="meta-whatsapp-webhook"),
    # Outbound messaging endpoint for studio admin
    path("messages/send/", OutboundMessageDispatchView.as_view(), name="outbound-send"),
    path("health/", IntegrationHealthView.as_view(), name="integration-health"),
    # OAuth endpoints for Meta Business Login
    path("oauth/instagram/login/", InstagramOAuthStartView.as_view(), name="oauth-instagram-login"),
    path("oauth/instagram/callback/", InstagramOAuthCallbackView.as_view(), name="oauth-instagram-callback"),
    path("oauth/instagram/deauthorize/", InstagramDeauthorizeView.as_view(), name="oauth-instagram-deauthorize"),
    path("oauth/instagram/data-deletion/", InstagramDataDeletionView.as_view(), name="oauth-instagram-data-deletion"),
]
