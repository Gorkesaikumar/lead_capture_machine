"""
Serializers for Scheduling, Availability, and Studio Operating Hours.
"""
from rest_framework import serializers
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability
from apps.services.models import Package, PhotographyService


class WeeklyAvailabilitySerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = WeeklyAvailability
        fields = (
            "id",
            "weekday",
            "weekday_display",
            "start_time",
            "end_time",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, data):
        start_time = data.get("start_time", getattr(self.instance, "start_time", None))
        end_time = data.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return data


class SpecialAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialAvailability
        fields = (
            "id",
            "date",
            "start_time",
            "end_time",
            "reason",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, data):
        start_time = data.get("start_time", getattr(self.instance, "start_time", None))
        end_time = data.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return data


class BlockedPeriodSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = BlockedPeriod
        fields = (
            "id",
            "starts_at",
            "ends_at",
            "reason",
            "service",
            "service_name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, data):
        starts_at = data.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = data.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError({"ends_at": "End datetime must be after start datetime."})
        return data


class HolidayClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayClosure
        fields = (
            "id",
            "date",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AvailabilityQuerySerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(
        queryset=PhotographyService.objects.filter(is_deleted=False, is_active=True),
        required=True,
    )
    package = serializers.PrimaryKeyRelatedField(
        queryset=Package.objects.filter(is_deleted=False, is_active=True),
        required=False,
        allow_null=True,
    )
    date = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    slot_step = serializers.IntegerField(required=False, default=30, min_value=5, max_value=240)

    def validate(self, data):
        if not data.get("date") and not (data.get("start_date") and data.get("end_date")):
            raise serializers.ValidationError("Either 'date' or both 'start_date' and 'end_date' must be provided.")
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return data
