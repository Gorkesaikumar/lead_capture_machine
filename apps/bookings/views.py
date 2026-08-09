"""
Views for Booking Links, Public Customer Booking flow, and Admin Booking Management.
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from apps.bookings.models import Booking, BookingLink
from apps.bookings.serializers import (
    BookingAdminSerializer,
    BookingLinkPublicDetailSerializer,
    CreateBookingLinkSerializer,
    PublicBookingConfirmationResultSerializer,
    PublicBookingConfirmSerializer,
)
from apps.bookings.services import (
    BookingLinkService,
    BookingService,
    BookingValidationError,
    ScheduleUnavailableError,
    SlotConflictError,
)
from apps.scheduling.services import AvailabilityService
from apps.services.models import Package, PhotographyService


class PublicBookingLinkDetailView(APIView):
    """
    Public endpoint for customer to view their booking link details.
    GET /api/v1/bookings/links/<token>/
    """

    permission_classes = [AllowAny]

    def get(self, request, token: str, *args, **kwargs):
        try:
            link = BookingLinkService.validate_link(token, allow_used=True)
        except BookingValidationError as exc:
            return Response(
                {"error": "invalid_link", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookingLinkPublicDetailSerializer(link)
        return Response(serializer.data)


class PublicBookingLinkAvailabilityView(APIView):
    """
    Public endpoint for customer to view available booking slots for their link.
    GET /api/v1/bookings/links/<token>/availability/?date=YYYY-MM-DD
    """

    permission_classes = [AllowAny]

    def get(self, request, token: str, *args, **kwargs):
        try:
            link = BookingLinkService.validate_link(token)
        except BookingValidationError as exc:
            return Response(
                {"error": "invalid_link", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Service determination: from link or query params
        service = link.service
        if not service:
            service_id = request.query_params.get("service") or request.query_params.get("service_id")
            if service_id:
                try:
                    service = PhotographyService.objects.get(id=service_id, is_deleted=False, is_active=True)
                except (PhotographyService.DoesNotExist, ValueError):
                    return Response(
                        {"error": "invalid_service", "message": "Specified service not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {"error": "missing_service", "message": "Please specify a service query parameter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        package = None
        package_id = request.query_params.get("package") or request.query_params.get("package_id")
        if package_id:
            try:
                package = Package.objects.get(id=package_id, service=service, is_deleted=False, is_active=True)
            except (Package.DoesNotExist, ValueError):
                pass

        date_str = request.query_params.get("date")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if date_str:
            target_date = parse_date(date_str)
            if not target_date:
                return Response(
                    {"error": "invalid_date", "message": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            slots = AvailabilityService.get_available_slots(
                service=service,
                target_date=target_date,
                package=package,
            )
            return Response({
                "service_id": str(service.id),
                "service_name": service.name,
                "date": target_date.isoformat(),
                "timezone": str(AvailabilityService.get_studio_timezone()),
                "slots_count": len(slots),
                "slots": slots,
            })

        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                return Response(
                    {"error": "invalid_date", "message": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                range_data = AvailabilityService.get_range_availability(
                    service=service,
                    start_date=start_date,
                    end_date=end_date,
                    package=package,
                )
                return Response(range_data)
            except ValueError as exc:
                return Response(
                    {"error": "invalid_range", "message": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"error": "missing_date", "message": "Provide either 'date' or 'start_date' and 'end_date'."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PublicBookingConfirmView(APIView):
    """
    Public endpoint for customer to finalize and confirm an appointment slot.
    POST /api/v1/bookings/links/<token>/confirm/
    """

    permission_classes = [AllowAny]

    def post(self, request, token: str, *args, **kwargs):
        serializer = PublicBookingConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = None
        if data.get("service_id"):
            try:
                service = PhotographyService.objects.get(
                    id=data["service_id"], is_deleted=False, is_active=True
                )
            except PhotographyService.DoesNotExist:
                return Response(
                    {"error": "invalid_service", "message": "Specified service not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        package = None
        if data.get("package_id"):
            try:
                package = Package.objects.get(
                    id=data["package_id"], is_deleted=False, is_active=True
                )
            except Package.DoesNotExist:
                return Response(
                    {"error": "invalid_package", "message": "Specified package not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            booking = BookingService.create_booking(
                booking_link_token=token,
                starts_at=data["starts_at"],
                service=service,
                package=package,
                customer_notes=data.get("customer_notes", ""),
                customer_name=data.get("customer_name", ""),
                customer_phone=data.get("customer_phone", ""),
                customer_email=data.get("customer_email"),
            )
            result_serializer = PublicBookingConfirmationResultSerializer(booking)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        except SlotConflictError as exc:
            return Response(
                {"error": "slot_conflict", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except (ScheduleUnavailableError, BookingValidationError) as exc:
            return Response(
                {"error": "booking_error", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin endpoint to view and manage bookings.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BookingAdminSerializer
    queryset = (
        Booking.objects.filter(is_deleted=False)
        .select_related("customer", "lead", "service", "package")
        .order_by("-starts_at")
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "service", "customer"]
    search_fields = ["customer__display_name", "customer_notes", "internal_notes"]
    ordering_fields = ["starts_at", "booked_at", "created_at"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        reason = request.data.get("reason", "")
        internal_notes = request.data.get("internal_notes", "")
        updated_booking = BookingService.cancel_booking(
            booking=booking,
            reason=reason,
            internal_notes=internal_notes,
            cancelled_by=request.user,
        )
        serializer = self.get_serializer(updated_booking)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminBookingLinkCreateView(APIView):
    """
    Admin endpoint to generate a secure booking link for a sales lead.
    POST /api/v1/bookings/links/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = CreateBookingLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        link = BookingLinkService.create_for_lead(
            lead=data["lead"],
            service=data.get("service"),
            expires_in_days=data.get("expires_in_days", 7),
            created_by=request.user,
        )

        return Response(
            {
                "id": str(link.id),
                "lead_id": str(link.lead_id),
                "token": link.token,
                "expires_at": link.expires_at.isoformat(),
                "booking_url": f"/book/{link.token}",
                "is_used": link.is_used,
            },
            status=status.HTTP_201_CREATED,
        )
