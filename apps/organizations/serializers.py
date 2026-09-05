from rest_framework import serializers
from apps.organizations.models import Organization, OrganizationMembership, OrganizationInvitation
from apps.accounts.models import User

class OrganizationSerializer(serializers.ModelSerializer):
    def validate_timezone(self, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise serializers.ValidationError("Enter a valid IANA timezone, such as Asia/Kolkata.")
        return value

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "logo", "contact_email", "contact_phone", "timezone", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "is_active", "created_at", "updated_at"]


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "role", "is_active", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def validate_role(self, value):
        if value == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError("Cannot set role to OWNER through this endpoint.")
        return value


class OrganizationInvitationSerializer(serializers.ModelSerializer):
    invited_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = ["id", "email", "role", "invited_by", "status", "expires_at", "created_at"]
        read_only_fields = ["id", "invited_by", "status", "expires_at", "created_at"]


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.MEMBER,
        ]
    )

class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
