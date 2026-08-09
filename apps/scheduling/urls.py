"""
URL configuration for Scheduling and Availability.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.scheduling.views import (
    AvailabilityAPIView,
    BlockedPeriodViewSet,
    HolidayClosureViewSet,
    SpecialAvailabilityViewSet,
    WeeklyAvailabilityViewSet,
)

app_name = "scheduling"

router = DefaultRouter()
router.register("weekly", WeeklyAvailabilityViewSet, basename="weekly-availability")
router.register("special", SpecialAvailabilityViewSet, basename="special-availability")
router.register("blocked-periods", BlockedPeriodViewSet, basename="blocked-period")
router.register("holidays", HolidayClosureViewSet, basename="holiday-closure")

urlpatterns = [
    path("availability/", AvailabilityAPIView.as_view(), name="availability"),
] + router.urls
