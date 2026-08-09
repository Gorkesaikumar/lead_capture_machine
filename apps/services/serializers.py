"""
Serializers for Photography Services and Packages.
"""
from decimal import Decimal
from rest_framework import serializers
from apps.services.models import Package, PhotographyService


class PackageSerializer(serializers.ModelSerializer):
    """
    Serializer for Package CRUD and nested representation.
    """

    service_name = serializers.CharField(source="service.name", read_only=True)
    effective_duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Package
        fields = (
            "id",
            "service",
            "service_name",
            "name",
            "slug",
            "description",
            "price",
            "duration_minutes_override",
            "effective_duration_minutes",
            "inclusions",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "effective_duration_minutes", "created_at", "updated_at")

    def validate_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_duration_minutes_override(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Duration override must be at least 1 minute.")
        return value

    def validate_inclusions(self, value):
        if not isinstance(value, (list, dict)):
            raise serializers.ValidationError("Inclusions must be a JSON array or object.")
        return value


class PhotographyServiceListSerializer(serializers.ModelSerializer):
    """
    Summary serializer for Photography Services listing.
    """

    packages_count = serializers.SerializerMethodField()
    packages = serializers.SerializerMethodField()
    total_slot_duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = PhotographyService
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "duration_minutes",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "total_slot_duration_minutes",
            "base_price",
            "packages",
            "packages_count",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_packages_count(self, obj) -> int:
        return obj.packages.filter(is_deleted=False).count()

    def get_packages(self, obj):
        active_pkgs = obj.packages.filter(is_deleted=False).order_by("sort_order", "price")
        return PackageSerializer(active_pkgs, many=True).data


class PhotographyServiceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a service including its active packages.
    """

    packages = serializers.SerializerMethodField()
    total_slot_duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = PhotographyService
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "duration_minutes",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "total_slot_duration_minutes",
            "base_price",
            "is_active",
            "sort_order",
            "packages",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_packages(self, obj):
        active_pkgs = obj.packages.filter(is_deleted=False).order_by("sort_order", "price")
        return PackageSerializer(active_pkgs, many=True).data


class PhotographyServiceCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Photography Services.
    """

    class Meta:
        model = PhotographyService
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "duration_minutes",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "base_price",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def validate_duration_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError("Session duration must be at least 1 minute.")
        return value

    def validate_buffer_before_minutes(self, value):
        if value < 0:
            raise serializers.ValidationError("Buffer before cannot be negative.")
        return value

    def validate_buffer_after_minutes(self, value):
        if value < 0:
            raise serializers.ValidationError("Buffer after cannot be negative.")
        return value

    def validate_base_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Base price cannot be negative.")
        return value
