"""
URL patterns for Bookings and Booking Links.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.bookings.views import (
    AdminBookingLinkCreateView,
    AdminBookingViewSet,
    PublicBookingConfirmView,
    PublicBookingLinkAvailabilityView,
    PublicBookingLinkDetailView,
)

app_name = "bookings"

router = DefaultRouter()
router.register("", AdminBookingViewSet, basename="admin-booking")

urlpatterns = [
    path("links/", AdminBookingLinkCreateView.as_view(), name="admin-link-create"),
    path("links/<str:token>/", PublicBookingLinkDetailView.as_view(), name="public-link-detail"),
    path("links/<str:token>/availability/", PublicBookingLinkAvailabilityView.as_view(), name="public-link-availability"),
    path("links/<str:token>/confirm/", PublicBookingConfirmView.as_view(), name="public-link-confirm"),
] + router.urls
