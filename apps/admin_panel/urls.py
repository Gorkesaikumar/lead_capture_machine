from django.urls import path
from apps.admin_panel.views import (
    AdminKPIsView,
    AdminAnalyticsView,
    AdminUsersView,
    AdminUserDetailView,
    AdminUserActionView,
    AdminSubscriptionPlansView,
    AdminRevenueView,
    AdminSystemView,
    AdminAuditLogsView,
)

app_name = "admin_panel"

urlpatterns = [
    path("kpis/", AdminKPIsView.as_view(), name="kpis"),
    path("analytics/", AdminAnalyticsView.as_view(), name="analytics"),
    path("users/", AdminUsersView.as_view(), name="users-list"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/action/", AdminUserActionView.as_view(), name="user-action"),
    path("subscriptions/plans/", AdminSubscriptionPlansView.as_view(), name="plans-list"),
    path("subscriptions/plans/<uuid:pk>/", AdminSubscriptionPlansView.as_view(), name="plan-detail"),
    path("revenue/", AdminRevenueView.as_view(), name="revenue"),
    path("system/", AdminSystemView.as_view(), name="system"),
    path("audit-logs/", AdminAuditLogsView.as_view(), name="audit-logs"),
]
