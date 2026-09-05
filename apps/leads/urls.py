"""
URL configuration for Leads and Lead Triggers endpoints.
"""
from rest_framework.routers import DefaultRouter
from apps.leads.views import LeadTriggerViewSet, LeadViewSet, LeadFormViewSet

app_name = "leads"

router = DefaultRouter()
router.register("triggers", LeadTriggerViewSet, basename="lead-trigger")
router.register("forms", LeadFormViewSet, basename="lead-form")
router.register("", LeadViewSet, basename="lead")

urlpatterns = router.urls
