"""
Main URL Configuration for Photo Studio CRM & Booking Platform.
"""
from django.contrib import admin
from django.urls import include, path
from apps.core.views import HealthLiveView, HealthReadyView
from apps.integrations.views import InstagramWebhookView, MetaWebhookBaseView, WhatsAppWebhookView
from apps.scheduling.views import AvailabilityAPIView
from apps.leads.public_views import PublicLeadSubmissionView

# API v1 URL patterns
api_v1_patterns = [
    path("health/ready/", HealthReadyView.as_view(), name="health_ready"),
    path("health/live/", HealthLiveView.as_view(), name="health_live"),
    path("availability/", AvailabilityAPIView.as_view(), name="availability"),
    path("auth/", include("apps.accounts.urls", namespace="auth")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("customers/", include("apps.customers.urls", namespace="customers")),
    path("leads/", include("apps.leads.urls", namespace="leads")),
    path("forms/<uuid:public_id>/submit/", PublicLeadSubmissionView.as_view(), name="public-form-submit"),
    path("automations/", include("apps.automations.urls")),
    path("conversations/", include("apps.conversations.urls", namespace="conversations")),
    path("webhooks/meta/instagram/", InstagramWebhookView.as_view(), name="webhook-meta-instagram"),
    path("webhooks/instagram/", InstagramWebhookView.as_view(), name="webhook-instagram"),
    path("webhooks/whatsapp/", WhatsAppWebhookView.as_view(), name="webhook-whatsapp"),
    path("webhooks/meta/", MetaWebhookBaseView.as_view(), name="webhook-meta"),
    path("webhooks/meta/whatsapp/", WhatsAppWebhookView.as_view(), name="webhook-meta-whatsapp"),
    path("integrations/", include("apps.integrations.urls", namespace="integrations")),
    path("organizations/", include("apps.organizations.urls")),
    path("services/", include("apps.services.urls", namespace="services")),
    path("scheduling/", include("apps.scheduling.urls", namespace="scheduling")),
    path("bookings/", include("apps.bookings.urls", namespace="bookings")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("audit/", include("apps.audit.urls", namespace="audit")),
    path("subscriptions/", include("apps.subscriptions.urls", namespace="subscriptions")),
    path("admin/", include("apps.admin_panel.urls", namespace="admin_panel")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # Top-level health endpoints for load balancers / container probes
    path("health/ready/", HealthReadyView.as_view(), name="root_health_ready"),
    path("health/live/", HealthLiveView.as_view(), name="root_health_live"),
    # Top-level webhook endpoints (matches Meta webhook configuration variants)
    path("webhook", MetaWebhookBaseView.as_view(), name="webhook-root-noslash"),
    path("webhook/", MetaWebhookBaseView.as_view(), name="webhook-root"),
    path("webhooks/meta/instagram/", InstagramWebhookView.as_view(), name="root-webhook-meta-instagram"),
    path("webhooks/meta/whatsapp/", WhatsAppWebhookView.as_view(), name="root-webhook-meta-whatsapp"),
    # Versioned API
    path("api/v1/", include((api_v1_patterns, "api_v1"))),
]
