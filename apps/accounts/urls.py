"""
URL configuration for Accounts and Authentication endpoints.
"""
from django.urls import path
from apps.accounts.views import CurrentAdminView, LoginView, LogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentAdminView.as_view(), name="me"),
]
