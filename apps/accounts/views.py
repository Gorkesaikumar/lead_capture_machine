"""
Authentication API Views for Admin Dashboard.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils.text import slugify
from apps.accounts.serializers import LoginSerializer, UserResponseSerializer
from apps.accounts.services import AuthService
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from rest_framework.authtoken.models import Token


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates Admin user and returns authentication token with safe profile details.
    """

    permission_classes = [AllowAny]
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token = serializer.validated_data["token"]
        user_data = UserResponseSerializer(user).data

        return Response(
            {
                "status": "success",
                "data": {
                    "token": token,
                    "user": user_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Revokes the current Admin's active authentication token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        AuthService.logout_admin(request.user)
        return Response(
            {
                "status": "success",
                "message": "Successfully logged out.",
            },
            status=status.HTTP_200_OK,
        )


class CurrentAdminView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the authenticated Admin's profile details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserResponseSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/password/change/
    Updates the authenticated Admin's password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"detail": "Both current_password and new_password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(current_password):
            return Response({"detail": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response({"detail": exc.messages}, status=400)
        user.set_password(new_password)
        user.save()
        Token.objects.filter(user=user).delete()
        return Response({"detail": "Password updated. Sign in again."}, status=status.HTTP_200_OK)


class SignupView(APIView):
    """
    POST /api/v1/auth/signup/
    Registers a new user, creates their organization, and returns an auth token.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        from rest_framework import serializers
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        name = serializers.CharField(min_length=2, max_length=255).run_validation(request.data.get("name") or request.data.get("full_name") or request.data.get("fullName"))
        email = serializers.EmailField().run_validation(request.data.get("email"))
        password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False).run_validation(request.data.get("password"))
        organization_name = serializers.CharField(min_length=2, max_length=180).run_validation(request.data.get("organization") or request.data.get("organization_name") or request.data.get("organizationName"))
        try:
            validate_password(password, user=User(email=email, full_name=name))
        except ValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})

        # Check for duplicate email
        normalized_email = User.objects.normalize_email(email)
        if User.objects.filter(email__iexact=normalized_email).exists():
            return Response(
                {
                    "status": "error",
                    "detail": "An account with this email already exists.",
                    "errors": {"email": "An account with this email already exists. Please sign in instead."},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=normalized_email,
                    password=password,
                    full_name=name,
                )

                # Generate unique org slug
                base_slug = slugify(organization_name) or "workspace"
                slug = base_slug
                counter = 1
                while Organization.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create organization
                org = Organization.objects.create(
                    name=organization_name,
                    slug=slug,
                    owner=user,
                )

                # Add owner membership
                OrganizationMembership.objects.create(
                    organization=org,
                    user=user,
                    role=OrganizationMembership.Role.OWNER,
                    is_active=True,
                )

                # Provision Free Plan subscription tier automatically (10 monthly leads credit)
                from apps.subscriptions.services import SubscriptionEntitlementService
                SubscriptionEntitlementService.get_or_create_active_subscription(org)

                # Create auth token
                token, _ = Token.objects.get_or_create(user=user)

            from apps.accounts.recovery import send_verification_email
            email_delivery = send_verification_email(user)
            user_data = UserResponseSerializer(user).data
            return Response(
                {
                    "status": "success",
                    "data": {
                        "token": token.key,
                        "user": user_data,
                        "organization_id": str(org.id),
                        "verification_email": email_delivery,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Signup failed: {exc}", exc_info=True)
            return Response(
                {"status": "error", "detail": "Something went wrong while creating your account. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
