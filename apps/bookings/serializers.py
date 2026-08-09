"""
Serializers for Bookings and Public Booking Links.
"""
from rest_framework import serializers
from django.conf import settings
from apps.bookings.models import Booking, BookingLink
from apps.leads.models import Lead
from apps.notifications.models import Notification
from apps.services.models import Package, PhotographyService
from apps.services.serializers import PackageSerializer, PhotographyServiceDetailSerializer


class BookingLinkPublicDetailSerializer(serializers.ModelSerializer):
    """
    Public representation of a booking link for the customer's browser view.
    Does not expose sensitive internal data or other customers' information.
    """

    studio_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="lead.customer.display_name", read_only=True)
    service = PhotographyServiceDetailSerializer(read_only=True)
    available_services = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    booking = serializers.SerializerMethodField()

    class Meta:
        model = BookingLink
        fields = (
            "token",
            "studio_name",
            "customer_name",
            "service",
            "available_services",
            "expires_at",
            "is_used",
            "is_revoked",
            "is_expired",
            "booking",
        )

    def get_studio_name(self, obj) -> str:
        return getattr(settings, "STUDIO_NAME", "Studio V4 Photography")

    def get_is_expired(self, obj) -> bool:
        return not obj.is_valid

    def get_available_services(self, obj):
        # If link is bound to a specific service, return just that service's packages
        if obj.service:
            return PhotographyServiceDetailSerializer([obj.service], many=True).data
        # Otherwise return all active studio services
        active_services = PhotographyService.objects.filter(
            is_deleted=False, is_active=True
        ).prefetch_related("packages")
        return PhotographyServiceDetailSerializer(active_services, many=True).data

    def get_booking(self, obj):
        if not obj.is_used:
            return None
        # Retrieve the latest booking associated with the lead
        booking = obj.lead.bookings.filter(is_deleted=False).order_by("-created_at").first()
        if not booking:
            return None
        return {
            "id": str(booking.id),
            "starts_at": booking.starts_at.isoformat(),
            "ends_at": booking.ends_at.isoformat(),
            "service_name": booking.service.name if booking.service else None,
            "package_name": booking.package.name if booking.package else None,
            "status": booking.status,
        }


class PublicBookingConfirmSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField(required=True)
    service_id = serializers.UUIDField(required=False, allow_null=True)
    package_id = serializers.UUIDField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=True, max_length=255)
    customer_phone = serializers.CharField(required=True, max_length=50)
    customer_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_customer_phone(self, value):
        import re
        # Strip all non-digit characters except leading '+'
        cleaned = re.sub(r"[^\d+]", "", value)
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"
        # Basic length validation for E.164 (usually between 10 to 15 digits excluding '+')
        if not re.match(r"^\+\d{10,15}$", cleaned):
            raise serializers.ValidationError("Please provide a valid phone number with country code (e.g., +919876543210).")
        return cleaned


class PublicBookingConfirmationResultSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True, default=None)

    class Meta:
        model = Booking
        fields = (
            "id",
            "customer_name",
            "service_name",
            "package_name",
            "starts_at",
            "ends_at",
            "duration_minutes",
            "status",
            "booked_at",
        )


class BookingAdminSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.primary_phone", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True, default=None)
    whatsapp_notification = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "lead",
            "service",
            "service_name",
            "package",
            "package_name",
            "starts_at",
            "ends_at",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "blocked_starts_at",
            "blocked_ends_at",
            "duration_minutes",
            "status",
            "customer_notes",
            "internal_notes",
            "booked_at",
            "cancelled_at",
            "created_at",
            "updated_at",
            "whatsapp_notification",
        )
        read_only_fields = (
            "id",
            "blocked_starts_at",
            "blocked_ends_at",
            "duration_minutes",
            "booked_at",
            "created_at",
            "updated_at",
        )

    def get_whatsapp_notification(self, obj) -> dict | None:
        notification = Notification.objects.filter(
            idempotency_key=f"booking_conf_{obj.id}"
        ).first()
        if not notification:
            return None
        return {
            "status": notification.status,
            "error_message": notification.error_message,
            "retry_count": notification.retry_count,
            "is_permanent_error": notification.is_permanent_error,
        }


class CreateBookingLinkSerializer(serializers.Serializer):
    lead = serializers.PrimaryKeyRelatedField(
        queryset=Lead.objects.filter(is_deleted=False),
        required=True,
    )
    service = serializers.PrimaryKeyRelatedField(
        queryset=PhotographyService.objects.filter(is_deleted=False, is_active=True),
        required=False,
        allow_null=True,
    )
    expires_in_days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=60)
