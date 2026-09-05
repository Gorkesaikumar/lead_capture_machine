"""
Serializers for Admin Authentication and Profile representations.
"""
from rest_framework import serializers
from apps.accounts.models import User
from apps.accounts.services import AuthService


class LoginSerializer(serializers.Serializer):
    """
    Validates admin login credentials and delegates authentication to AuthService.
    """

    email = serializers.EmailField(
        required=True,
        write_only=True,
        error_messages={"required": "Email is required.", "invalid": "Enter a valid email address."},
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        trim_whitespace=False,
        error_messages={"required": "Password is required."},
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        request = self.context.get("request")
        ip_address = request.META.get("REMOTE_ADDR") if request else None

        user, token_key = AuthService.authenticate_admin(
            email=email,
            password=password,
            ip_address=ip_address,
        )

        attrs["user"] = user
        attrs["token"] = token_key
        return attrs


class UserResponseSerializer(serializers.ModelSerializer):
    """
    Safe public/client representation of an Admin User.
    Excludes password, password hashes, and internal framework flags.
    """

    workspaces = serializers.SerializerMethodField()

    def get_workspaces(self, user):
        memberships = user.memberships.filter(
            is_active=True,
            organization__is_active=True,
            organization__is_deleted=False,
        ).select_related("organization").order_by("created_at", "id")
        return [
            {"id": str(m.organization_id), "name": m.organization.name, "role": m.role}
            for m in memberships
        ]

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "created_at",
            "workspaces",
        )
        read_only_fields = fields


class LoginResponseSerializer(serializers.Serializer):
    """
    Encapsulates the successful login payload.
    """

    token = serializers.CharField(read_only=True)
    user = UserResponseSerializer(read_only=True)
