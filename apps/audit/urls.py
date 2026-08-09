"""
URL configuration for the Audit module.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.audit.views import AuditEventReadOnlyViewSet

app_name = "audit"

router = DefaultRouter()
router.register(r"", AuditEventReadOnlyViewSet, basename="audit-event")

urlpatterns = [
    path("", include(router.urls)),
]
