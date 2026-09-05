"""
URL configuration for Accounts and Authentication endpoints.
"""
from django.urls import path
from apps.accounts.views import CurrentAdminView, LoginView, LogoutView, ChangePasswordView, SignupView

from apps.accounts.recovery import PasswordResetView, PasswordResetConfirmView, EmailVerifyView, EmailVerificationResendView

app_name = "accounts"

urlpatterns = [
    path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", EmailVerificationResendView.as_view(), name="email-resend"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("login/", LoginView.as_view(), name="login"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentAdminView.as_view(), name="me"),
    path("password/change/", ChangePasswordView.as_view(), name="change_password"),
]
