"""
URL patterns for Core app.
"""
from django.urls import path
from apps.core.views import HealthCheckView, PingView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("ping/", PingView.as_view(), name="ping"),
]
