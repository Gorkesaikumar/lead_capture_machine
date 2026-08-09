"""
URL Configuration for Analytics endpoints.
"""
from django.urls import path
from apps.analytics.views import (
    BookingsAnalyticsAPIView,
    DashboardSummaryAPIView,
    LeadsAnalyticsAPIView,
    ServicesAnalyticsAPIView,
)

app_name = "analytics"

urlpatterns = [
    path("dashboard/", DashboardSummaryAPIView.as_view(), name="dashboard-summary"),
    path("summary/", DashboardSummaryAPIView.as_view(), name="summary"),
    path("leads/", LeadsAnalyticsAPIView.as_view(), name="leads-analytics"),
    path("bookings/", BookingsAnalyticsAPIView.as_view(), name="bookings-analytics"),
    path("services/", ServicesAnalyticsAPIView.as_view(), name="services-analytics"),
]
