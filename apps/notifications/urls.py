"""
URL configuration for Notifications module.
"""
from django.urls import path
from apps.notifications.views import (
    NotificationDetailView,
    NotificationListView,
    NotificationRetryView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
    path("<uuid:pk>/retry/", NotificationRetryView.as_view(), name="notification-retry"),
]
