"""
Views for Scheduling, Availability, and Business Hours.
"""
from rest_framework import filters, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit.services import AuditService
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability
from apps.scheduling.serializers import (
    AvailabilityQuerySerializer,
    BlockedPeriodSerializer,
    HolidayClosureSerializer,
    SpecialAvailabilitySerializer,
    WeeklyAvailabilitySerializer,
)
from apps.scheduling.services import AvailabilityService


class AvailabilityAPIView(APIView):
    """
    Public/advisory endpoint to compute available booking slots.
    GET /api/v1/availability/?service=<id>&date=YYYY-MM-DD
    GET /api/v1/scheduling/availability/?service=<id>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        serializer = AvailabilityQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = data["service"]
        package = data.get("package")
        slot_step = data.get("slot_step", 30)

        # Single date query
        if data.get("date"):
            target_date = data["date"]
            slots = AvailabilityService.get_available_slots(
                service=service,
                target_date=target_date,
                package=package,
                slot_step_minutes=slot_step,
            )
            return Response({
                "service_id": str(service.id),
                "service_name": service.name,
                "package_id": str(package.id) if package else None,
                "package_name": package.name if package else None,
                "date": target_date.isoformat(),
                "weekday": target_date.strftime("%A"),
                "timezone": str(AvailabilityService.get_studio_timezone()),
                "slots_count": len(slots),
                "slots": slots,
            })

        # Date range query
        start_date = data["start_date"]
        end_date = data["end_date"]
        range_data = AvailabilityService.get_range_availability(
            service=service,
            start_date=start_date,
            end_date=end_date,
            package=package,
            slot_step_minutes=slot_step,
        )
        return Response(range_data)


class WeeklyAvailabilityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WeeklyAvailabilitySerializer
    queryset = WeeklyAvailability.objects.all().order_by("weekday", "start_time")
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["weekday", "is_active"]
    ordering_fields = ["weekday", "start_time"]

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="WeeklyAvailability",
            entity_id=instance.id,
            change_type="create",
            metadata={"weekday": instance.weekday, "start_time": str(instance.start_time), "end_time": str(instance.end_time)},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="WeeklyAvailability",
            entity_id=instance.id,
            change_type="update",
            metadata={"weekday": instance.weekday, "start_time": str(instance.start_time), "end_time": str(instance.end_time), "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_availability_changed(
            entity_type="WeeklyAvailability",
            entity_id=instance.id,
            change_type="delete",
            metadata={"weekday": instance.weekday},
            request=self.request,
        )
        instance.delete()


class SpecialAvailabilityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SpecialAvailabilitySerializer
    queryset = SpecialAvailability.objects.all().order_by("date", "start_time")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["date", "is_active"]
    search_fields = ["reason"]
    ordering_fields = ["date", "start_time"]

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="SpecialAvailability",
            entity_id=instance.id,
            change_type="create",
            metadata={"date": str(instance.date), "start_time": str(instance.start_time), "end_time": str(instance.end_time)},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="SpecialAvailability",
            entity_id=instance.id,
            change_type="update",
            metadata={"date": str(instance.date), "start_time": str(instance.start_time), "end_time": str(instance.end_time), "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_availability_changed(
            entity_type="SpecialAvailability",
            entity_id=instance.id,
            change_type="delete",
            metadata={"date": str(instance.date)},
            request=self.request,
        )
        instance.delete()


class BlockedPeriodViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BlockedPeriodSerializer
    queryset = BlockedPeriod.objects.all().select_related("service").order_by("starts_at")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["service", "is_active"]
    search_fields = ["reason"]
    ordering_fields = ["starts_at", "ends_at"]

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="BlockedPeriod",
            entity_id=instance.id,
            change_type="create",
            metadata={"starts_at": instance.starts_at.isoformat(), "ends_at": instance.ends_at.isoformat(), "reason": instance.reason},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="BlockedPeriod",
            entity_id=instance.id,
            change_type="update",
            metadata={"starts_at": instance.starts_at.isoformat(), "ends_at": instance.ends_at.isoformat(), "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_availability_changed(
            entity_type="BlockedPeriod",
            entity_id=instance.id,
            change_type="delete",
            metadata={"starts_at": instance.starts_at.isoformat(), "ends_at": instance.ends_at.isoformat()},
            request=self.request,
        )
        instance.delete()


class HolidayClosureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HolidayClosureSerializer
    queryset = HolidayClosure.objects.all().order_by("date")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["date", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["date"]

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="HolidayClosure",
            entity_id=instance.id,
            change_type="create",
            metadata={"date": str(instance.date), "name": instance.name},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_availability_changed(
            entity_type="HolidayClosure",
            entity_id=instance.id,
            change_type="update",
            metadata={"date": str(instance.date), "name": instance.name, "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_availability_changed(
            entity_type="HolidayClosure",
            entity_id=instance.id,
            change_type="delete",
            metadata={"date": str(instance.date), "name": instance.name},
            request=self.request,
        )
        instance.delete()

