from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Comprehensive tests for Scheduling and Dynamic Availability Engine.
Covers business hours, multiple periods / breaks, buffers, service durations,
blocked periods, holiday closures, booking collisions, timezone boundaries, and REST APIs.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from django.utils import timezone
from rest_framework import status
from apps.bookings.models import Booking
from apps.customers.models import Customer
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability
from apps.scheduling.services import AvailabilityService
from apps.services.models import Package, PhotographyService


@pytest.fixture
def studio_tz():
    return AvailabilityService.get_studio_timezone()


@pytest.fixture
def future_monday():
    """Returns a guaranteed future Monday date."""
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead <= 0:
        days_ahead += 7
    # Ensure it's at least 2 weeks ahead to avoid any past-time filter on today
    return today + timedelta(days=days_ahead + 7)


@pytest.fixture
def portrait_service():
    return PhotographyService.objects.create(organization=test_workspace(),
        name="Studio Portrait Session",
        duration_minutes=60,
        buffer_before_minutes=0,
        buffer_after_minutes=0,
        base_price=Decimal("5000.00"),
    )


@pytest.fixture
def buffered_service():
    return PhotographyService.objects.create(organization=test_workspace(),
        name="Newborn Luxury Session",
        duration_minutes=60,
        buffer_before_minutes=15,
        buffer_after_minutes=15,
        base_price=Decimal("8000.00"),
    )


@pytest.mark.django_db
class TestAvailabilityEngine:
    def test_normal_day_availability(self, portrait_service, future_monday):
        """Standard business hours 09:00 - 13:00 produces exact hourly slots."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,  # Monday
            start_time=time(9, 0),
            end_time=time(13, 0),
        )

        slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
            slot_step_minutes=60,
        )

        assert len(slots) == 4
        assert "09:00:00" in slots[0]["starts_at"]
        assert "10:00:00" in slots[1]["starts_at"]
        assert "11:00:00" in slots[2]["starts_at"]
        assert "12:00:00" in slots[3]["starts_at"]

    def test_closed_day_and_holiday_closure(self, portrait_service, future_monday):
        """HolidayClosure overrides weekly hours and marks the studio as completely closed."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        HolidayClosure.objects.create(organization=test_workspace(),
            date=future_monday,
            name="Studio Maintenance Day",
        )

        slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
        )
        assert slots == []

    def test_mid_day_break_multiple_periods(self, portrait_service, future_monday):
        """Multiple operating periods (09:00-13:00, 14:00-18:00) respects 13:00-14:00 lunch break."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(14, 0),
            end_time=time(18, 0),
        )

        slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
            slot_step_minutes=60,
        )

        # 4 slots in morning (09, 10, 11, 12), 4 slots in afternoon (14, 15, 16, 17)
        assert len(slots) == 8
        start_times = [s["starts_at"] for s in slots]
        assert not any("13:00:00" in t for t in start_times)
        assert any("14:00:00" in t for t in start_times)

    def test_blocked_period_generic_and_service_specific(self, portrait_service, buffered_service, future_monday, studio_tz):
        """Blocked periods eliminate overlapping slots for all or specific services."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Block 11:00 to 13:00 specifically for portrait_service
        block_start = timezone.make_aware(datetime.combine(future_monday, time(11, 0)), studio_tz)
        block_end = timezone.make_aware(datetime.combine(future_monday, time(13, 0)), studio_tz)
        BlockedPeriod.objects.create(organization=test_workspace(),
            starts_at=block_start,
            ends_at=block_end,
            reason="Special VIP Session",
            service=portrait_service,
        )

        portrait_slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
            slot_step_minutes=60,
        )
        # Blocked 11:00-13:00 should remove 11:00 and 12:00 slots for portrait_service
        portrait_times = [s["starts_at"] for s in portrait_slots]
        assert not any("11:00:00" in t for t in portrait_times)
        assert not any("12:00:00" in t for t in portrait_times)

        # buffered_service should NOT be blocked by portrait_service's specific block
        buffered_slots = AvailabilityService.get_available_slots(
            service=buffered_service,
            target_date=future_monday,
            slot_step_minutes=60,
        )
        buffered_times = [s["starts_at"] for s in buffered_slots]
        assert any("11:00:00" in t for t in buffered_times)

    def test_existing_booking_collision_with_buffers(self, buffered_service, future_monday, studio_tz):
        """Booking with preparation and cleanup buffers blocks adjacent candidate slots."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        customer = Customer.objects.create(organization=test_workspace(), display_name="Ananya Panday")

        # Booking at 11:00 - 12:00 with 15m before and 15m after buffer
        booking_start = timezone.make_aware(datetime.combine(future_monday, time(11, 0)), studio_tz)
        booking_end = timezone.make_aware(datetime.combine(future_monday, time(12, 0)), studio_tz)
        Booking.objects.create(
            customer=customer,
            service=buffered_service,
            starts_at=booking_start,
            ends_at=booking_end,
            buffer_before_minutes=15,
            buffer_after_minutes=15,
            status=Booking.Status.CONFIRMED,
        )

        slots = AvailabilityService.get_available_slots(
            service=buffered_service,
            target_date=future_monday,
            slot_step_minutes=30,
        )
        start_times = [s["starts_at"] for s in slots]

        # 11:00:00 is booked -> not available
        assert not any("11:00:00" in t for t in start_times)
        # 10:30:00 candidate (10:30-11:30 + 15m after = 11:45) overlaps with booking (10:45-12:15) -> not available
        assert not any("10:30:00" in t for t in start_times)

    def test_package_duration_override(self, portrait_service, future_monday):
        """Package duration override alters available slot lengths."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        pkg_extended = Package.objects.create(
            service=portrait_service,
            name="Extended Session",
            price=Decimal("10000.00"),
            duration_minutes_override=120,
        )

        slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
            package=pkg_extended,
            slot_step_minutes=60,
        )

        # 09:00-11:00 and 10:00-12:00 and 11:00-13:00 fit inside 09:00-13:00
        assert len(slots) == 3
        for s in slots:
            assert s["duration_minutes"] == 120

    def test_special_availability_override(self, portrait_service, future_monday):
        """SpecialAvailability overrides regular weekly hours for a specific date."""
        # Regular weekly hours: 09:00 - 12:00
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        # Special hours on this specific date: 15:00 - 19:00
        SpecialAvailability.objects.create(organization=test_workspace(),
            date=future_monday,
            start_time=time(15, 0),
            end_time=time(19, 0),
            reason="Evening Special",
        )

        slots = AvailabilityService.get_available_slots(
            service=portrait_service,
            target_date=future_monday,
            slot_step_minutes=60,
        )

        # Should only have evening slots: 15:00, 16:00, 17:00, 18:00
        assert len(slots) == 4
        start_times = [s["starts_at"] for s in slots]
        assert any("15:00:00" in t for t in start_times)
        assert not any("09:00:00" in t for t in start_times)

    def test_range_availability_calculation(self, portrait_service, future_monday):
        """Range availability returns grouped days with metadata."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )

        range_result = AvailabilityService.get_range_availability(
            service=portrait_service,
            start_date=future_monday,
            end_date=future_monday + timedelta(days=2),
            slot_step_minutes=60,
        )

        assert range_result["service_name"] == "Studio Portrait Session"
        assert len(range_result["days"]) == 3
        # Monday has 3 slots (09, 10, 11), Tuesday and Wednesday have 0
        assert range_result["days"][0]["slots_count"] == 3
        assert range_result["days"][1]["slots_count"] == 0


@pytest.mark.django_db
class TestSchedulingAPI:
    def test_public_availability_endpoint(self, api_client, portrait_service, future_monday):
        """Public advisory availability endpoint returns slot list without authentication."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )

        resp = api_client.get(
            f"/api/v1/availability/?service={portrait_service.id}&date={future_monday.isoformat()}&slot_step=60"
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["service_name"] == portrait_service.name
        assert data["slots_count"] == 4
        assert len(data["slots"]) == 4

    def test_public_range_availability_endpoint(self, api_client, portrait_service, future_monday):
        """Public endpoint supports date ranges."""
        WeeklyAvailability.objects.create(organization=test_workspace(),
            weekday=0,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        resp = api_client.get(
            f"/api/v1/availability/?service={portrait_service.id}&start_date={future_monday.isoformat()}&end_date={(future_monday + timedelta(days=1)).isoformat()}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["days"]) == 2

    def test_admin_weekly_availability_crud(self, authenticated_client):
        """Admin can configure weekly operating hours."""
        resp = authenticated_client.post(
            "/api/v1/scheduling/weekly/",
            data={
                "weekday": 1,  # Tuesday
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "is_active": True,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

        list_resp = authenticated_client.get("/api/v1/scheduling/weekly/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json()["count"] >= 1

    def test_admin_blocked_period_crud(self, authenticated_client, portrait_service, studio_tz):
        """Admin can block studio intervals."""
        start = timezone.now() + timedelta(days=3)
        end = start + timedelta(hours=4)
        resp = authenticated_client.post(
            "/api/v1/scheduling/blocked-periods/",
            data={
                "starts_at": start.isoformat(),
                "ends_at": end.isoformat(),
                "reason": "Studio Painting & Maintenance",
                "service": str(portrait_service.id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["reason"] == "Studio Painting & Maintenance"

    def test_admin_holiday_closure_crud(self, authenticated_client, future_monday):
        """Admin can declare holiday closures."""
        resp = authenticated_client.post(
            "/api/v1/scheduling/holidays/",
            data={
                "date": future_monday.isoformat(),
                "name": "Diwali Festival",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["name"] == "Diwali Festival"
