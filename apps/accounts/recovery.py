"""Expiring password reset tokens bound to the current password hash."""
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import User


def send_verification_email(user):
    if not settings.EMAIL_HOST and "locmem" not in settings.EMAIL_BACKEND:
        return "not_configured"
    token = signing.dumps({"user": str(user.pk), "email": user.email}, salt="email-verification")
    url = f"{settings.FRONTEND_URL}/verify-email?{urlencode({'token': token})}"
    try:
        send_mail("Verify your V4 Studio email", f"Verify your email address:\n{url}\nThis link expires in 24 hours.", settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        return "unavailable"
    return "accepted_by_mail_server"


class EmailVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth_login"

    def post(self, request):
        from django.utils import timezone
        try:
            data = signing.loads(request.data.get("token", ""), salt="email-verification", max_age=86400)
            user = User.objects.get(pk=data["user"], email=data["email"], is_active=True)
        except (signing.BadSignature, User.DoesNotExist, KeyError, ValueError, TypeError):
            raise serializers.ValidationError("Invalid or expired verification token.")
        if not user.email_verified_at:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
        return Response({"detail": "Email verified."})


class EmailVerificationResendView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "auth_login"

    def post(self, request):
        if request.user.email_verified_at:
            return Response({"detail": "Email already verified."})
        result = send_verification_email(request.user)
        if result != "accepted_by_mail_server":
            return Response({"detail": "Email delivery is unavailable. Contact your administrator."}, status=503)
        return Response({"detail": "Verification email accepted by the mail server."})


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth_login"

    def post(self, request):
        email = serializers.EmailField().run_validation(request.data.get("email"))
        if not settings.EMAIL_HOST and "locmem" not in settings.EMAIL_BACKEND:
            return Response({"detail": "Email delivery is not configured. Contact your administrator."}, status=503)
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            token = signing.dumps({"user": str(user.pk), "token": default_token_generator.make_token(user)}, salt="password-reset")
            url = f"{settings.FRONTEND_URL}/reset-password?{urlencode({'token': token})}"
            try:
                send_mail("Reset your V4 Studio password", f"Reset your password using this link:\n{url}\nThis link expires in one hour.", settings.DEFAULT_FROM_EMAIL, [user.email])
            except Exception:
                return Response({"detail": "Email delivery is unavailable. Please try again later."}, status=503)
        return Response({"detail": "If an active account exists, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth_login"

    @transaction.atomic
    def post(self, request):
        try:
            data = signing.loads(request.data.get("token", ""), salt="password-reset", max_age=3600)
            user = User.objects.select_for_update().get(pk=data["user"], is_active=True)
            if not default_token_generator.check_token(user, data["token"]):
                raise ValueError()
        except (signing.BadSignature, User.DoesNotExist, KeyError, ValueError, TypeError):
            raise serializers.ValidationError("Invalid or expired reset token.")
        password = serializers.CharField(max_length=128).run_validation(request.data.get("password"))
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        user.set_password(password)
        user.save(update_fields=["password"])
        Token.objects.filter(user=user).delete()
        return Response({"detail": "Password reset. Sign in again."})
