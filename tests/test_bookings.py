"""
Tests for Booking domain models, BookingLink lifecycle, ACID guarantees,
REST APIs, and PostgreSQL ExclusionConstraint concurrency collision prevention.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.bookings.models import Booking, BookingLink
from apps.bookings.services import (
    BookingLinkService,
    BookingService,
    BookingValidationError,
    ScheduleUnavailableError,
    SlotConflictError,
)
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity
from apps.scheduling.models import WeeklyAvailability
from apps.scheduling.services import AvailabilityService
from apps.services.models import PhotographyService

User = get_user_model()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="admin_booking@studio.com",
        password="SecureAdminPassword123!",
        full_name="Admin Booking",
    )


@pytest.fixture
def portrait_service():
    return PhotographyService.objects.create(
        name="Portrait Studio Session",
        slug="portrait-studio-session",
        description="Professional studio portrait session",
        duration_minutes=60,
        buffer_before_minutes=15,
        buffer_after_minutes=15,
        base_price=Decimal("150.00"),
        is_active=True,
    )


@pytest.fixture
def weekly_schedule():
    """Sets Monday-Friday 09:00 to 17:00 operating hours."""
    created = []
    for day in range(5):
        w = WeeklyAvailability.objects.create(
            weekday=day,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )
        created.append(w)
    return created


@pytest.fixture
def customer_lead(portrait_service):
    cust = Customer.objects.create(
        display_name="Alice Customer",
        primary_phone="+15551234567",
        email="alice@example.com",
    )
    lead = Lead.objects.create(
        customer=cust,
        source_channel="INSTAGRAM",
        service=portrait_service,
        status=Lead.Status.QUALIFIED,
    )
    return cust, lead


@pytest.mark.django_db(transaction=True)
class TestBookingLinkLifecycle:
    def test_create_booking_link_for_lead(self, admin_user, portrait_service, customer_lead):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(
            lead=lead,
            service=portrait_service,
            expires_in_days=5,
            created_by=admin_user,
        )

        assert link.token is not None
        assert len(link.token) >= 32
        assert link.is_valid is True
        assert link.is_used is False
        assert link.is_revoked is False
        assert link.expires_at > timezone.now()

        # Lead status transitioned
        lead.refresh_from_db()
        assert lead.status == Lead.Status.BOOKING_LINK_SENT

        # Activity logged
        activity = LeadActivity.objects.filter(
            lead=lead, activity_type=LeadActivity.ActivityType.BOOKING_LINK_SENT
        ).first()
        assert activity is not None
        assert activity.metadata["token"] == link.token

    def test_validate_link_states(self, customer_lead, portrait_service):
        cust, lead = customer_lead
        link = BookingLink.objects.create(
            lead=lead,
            service=portrait_service,
            expires_at=timezone.now() + timedelta(days=1),
        )

        # Valid link
        valid_link = BookingLinkService.validate_link(link.token)
        assert valid_link.id == link.id

        # Expired link
        link.expires_at = timezone.now() - timedelta(hours=1)
        link.save()
        with pytest.raises(BookingValidationError, match="expired"):
            BookingLinkService.validate_link(link.token)

        # Used link
        link.expires_at = timezone.now() + timedelta(days=1)
        link.is_used = True
        link.save()
        with pytest.raises(BookingValidationError, match="already been used"):
            BookingLinkService.validate_link(link.token)

        # Revoked link
        link.is_used = False
        link.is_revoked = True
        link.save()
        with pytest.raises(BookingValidationError, match="revoked"):
            BookingLinkService.validate_link(link.token)

        # Unknown token
        with pytest.raises(BookingValidationError, match="Invalid or non-existent"):
            BookingLinkService.validate_link("non_existent_token_12345")


from unittest.mock import patch

@pytest.mark.django_db(transaction=True)
@patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.delay")
class TestBookingServiceACID:
    def test_create_booking_atomic_success(self, mock_delay, admin_user, portrait_service, weekly_schedule, customer_lead):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service, created_by=admin_user)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        booking_start = timezone.make_aware(datetime.combine(target_date, time(10, 0)), tz)

        booking = BookingService.create_booking(
            booking_link_token=link.token,
            starts_at=booking_start,
            customer_notes="Please provide high-key backdrop.",
        )

        assert booking.id is not None
        assert booking.status == Booking.Status.CONFIRMED
        assert booking.customer == cust
        assert booking.lead == lead
        assert booking.service == portrait_service
        assert booking.starts_at == booking_start
        assert booking.ends_at == booking_start + timedelta(minutes=60)
        assert booking.blocked_starts_at == booking_start - timedelta(minutes=15)
        assert booking.blocked_ends_at == booking.ends_at + timedelta(minutes=15)
        assert booking.customer_notes == "Please provide high-key backdrop."

        # Link is marked as used
        link.refresh_from_db()
        assert link.is_used is True
        assert link.used_at is not None

        # Lead is marked as BOOKED
        lead.refresh_from_db()
        assert lead.status == Lead.Status.BOOKED
        assert lead.closed_at is not None

        # Activity logged
        activity = LeadActivity.objects.filter(
            lead=lead, activity_type=LeadActivity.ActivityType.STATUS_CHANGED
        ).order_by("-created_at").first()
        assert activity is not None
        assert "Appointment booked" in activity.description

    def test_create_booking_schedule_unavailable_rejected(self, mock_delay, portrait_service, weekly_schedule, customer_lead):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        # Outside operating hours (07:00 when studio opens at 09:00)
        invalid_start = timezone.make_aware(datetime.combine(target_date, time(7, 0)), tz)

        with pytest.raises(ScheduleUnavailableError):
            BookingService.create_booking(
                booking_link_token=link.token,
                starts_at=invalid_start,
            )

        # Ensure link and lead were not modified due to rollback
        link.refresh_from_db()
        lead.refresh_from_db()
        assert link.is_used is False
        assert lead.status == Lead.Status.BOOKING_LINK_SENT
        assert Booking.objects.count() == 0

    def test_booking_buffer_collision_rejected(self, mock_delay, admin_user, portrait_service, weekly_schedule, customer_lead):
        cust, lead = customer_lead
        link1 = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        booking1_start = timezone.make_aware(datetime.combine(target_date, time(10, 0)), tz)

        # Booking 1: 10:00 to 11:00 (blocked 09:45 to 11:15)
        BookingService.create_booking(
            booking_link_token=link1.token,
            starts_at=booking1_start,
        )

        # Create second customer & lead
        cust2 = Customer.objects.create(display_name="Bob Customer")
        lead2 = Lead.objects.create(customer=cust2, source_channel="WHATSAPP", service=portrait_service)
        link2 = BookingLinkService.create_for_lead(lead=lead2, service=portrait_service)

        # Attempt to book 11:00 to 12:00 (needs prep buffer 10:45, but Booking 1 cleanup is until 11:15)
        colliding_start = timezone.make_aware(datetime.combine(target_date, time(11, 0)), tz)

        with pytest.raises(SlotConflictError):
            BookingService.create_booking(
                booking_link_token=link2.token,
                starts_at=colliding_start,
            )

        assert Booking.objects.count() == 1

    def test_booking_cancellation_frees_slot(self, mock_delay, admin_user, portrait_service, weekly_schedule, customer_lead):
        cust, lead = customer_lead
        link1 = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        booking_start = timezone.make_aware(datetime.combine(target_date, time(10, 0)), tz)

        booking = BookingService.create_booking(
            booking_link_token=link1.token,
            starts_at=booking_start,
        )
        assert Booking.objects.filter(status=Booking.Status.CONFIRMED).count() == 1

        # Cancel the booking
        BookingService.cancel_booking(booking, reason="Client rescheduled travel")
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED
        assert booking.cancelled_at is not None

        # Now slot at 10:00 should be available again for a new customer
        cust2 = Customer.objects.create(display_name="Bob Customer")
        lead2 = Lead.objects.create(customer=cust2, source_channel="WHATSAPP", service=portrait_service)
        link2 = BookingLinkService.create_for_lead(lead=lead2, service=portrait_service)

        booking2 = BookingService.create_booking(
            booking_link_token=link2.token,
            starts_at=booking_start,
        )
        assert booking2.status == Booking.Status.CONFIRMED
        assert Booking.objects.filter(status=Booking.Status.CONFIRMED).count() == 1


@pytest.mark.django_db(transaction=True)
@patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.delay")
class TestPublicAndAdminBookingAPIs:
    def test_public_booking_link_detail_api(self, mock_delay, portrait_service, customer_lead):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        client = APIClient()
        response = client.get(f"/api/v1/bookings/links/{link.token}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["token"] == link.token
        assert data["customer_name"] == cust.display_name
        assert data["service"]["name"] == portrait_service.name
        assert data["is_used"] is False

    def test_public_booking_link_availability_api(self, mock_delay, portrait_service, weekly_schedule, customer_lead):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        client = APIClient()
        response = client.get(f"/api/v1/bookings/links/{link.token}/availability/?date=2026-08-10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["service_name"] == portrait_service.name
        assert data["slots_count"] > 0

    def test_public_booking_confirm_api(self, mock_delay, portrait_service, customer_lead, weekly_schedule):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        target_date = date(2026, 8, 10)
        tz = AvailabilityService.get_studio_timezone()
        booking_start = timezone.make_aware(datetime.combine(target_date, time(10, 0)), tz)

        client = APIClient()
        payload = {
            "starts_at": booking_start.isoformat(),
            "customer_name": cust.display_name,
            "customer_phone": cust.primary_phone,
            "customer_notes": "First photoshoot excited!",
        }
        response = client.post(f"/api/v1/bookings/links/{link.token}/confirm/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["service_name"] == portrait_service.name
        assert data["customer_name"] == cust.display_name

        # Re-using the same link should fail
        response2 = client.post(f"/api/v1/bookings/links/{link.token}/confirm/", payload, format="json")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_booking_list_and_cancel_api(self, mock_delay, admin_user, portrait_service, customer_lead, weekly_schedule):
        cust, lead = customer_lead
        link = BookingLinkService.create_for_lead(lead=lead, service=portrait_service)

        target_date = date(2026, 8, 10)
        tz = AvailabilityService.get_studio_timezone()
        booking_start = timezone.make_aware(datetime.combine(target_date, time(10, 0)), tz)

        booking = BookingService.create_booking(booking_link_token=link.token, starts_at=booking_start)

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # List bookings
        res = client.get("/api/v1/bookings/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()["results"]) == 1

        # Cancel booking
        cancel_res = client.post(
            f"/api/v1/bookings/{booking.id}/cancel/",
            {"reason": "Admin schedule override", "internal_notes": "Called client"},
            format="json",
        )
        assert cancel_res.status_code == status.HTTP_200_OK
        assert cancel_res.json()["status"] == "CANCELLED"


@pytest.mark.django_db(transaction=True)
@patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.delay")
class TestBookingConcurrencyAndExclusionConstraint:
    """
    CRITICAL CONCURRENCY TEST:
    Simulates two concurrent threads attempting to book the exact same time slot
    for two different customers simultaneously.
    Verifies that:
    1. Exactly one request succeeds (201 Created).
    2. Exactly one request fails with SlotConflictError (HTTP 409).
    3. The database contains EXACTLY ONE active booking.
    """

    def test_simultaneous_double_booking_race_condition(
        self, mock_delay, admin_user, portrait_service, weekly_schedule
    ):
        # 1. Prepare two distinct customers and leads
        cust1 = Customer.objects.create(display_name="Concurrent Alice", email="alice_race@test.com")
        lead1 = Lead.objects.create(customer=cust1, source_channel="INSTAGRAM", service=portrait_service)
        link1 = BookingLinkService.create_for_lead(lead=lead1, service=portrait_service)

        cust2 = Customer.objects.create(display_name="Concurrent Bob", email="bob_race@test.com")
        lead2 = Lead.objects.create(customer=cust2, source_channel="WHATSAPP", service=portrait_service)
        link2 = BookingLinkService.create_for_lead(lead=lead2, service=portrait_service)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        target_slot = timezone.make_aware(datetime.combine(target_date, time(14, 0)), tz)

        results = []

        def attempt_booking(token: str):
            connection.close()
            try:
                booking = BookingService.create_booking(
                    booking_link_token=token,
                    starts_at=target_slot,
                )
                return ("SUCCESS", str(booking.id))
            except SlotConflictError as err:
                return ("CONFLICT", str(err))
            except Exception as exc:
                return ("ERROR", str(exc))
            finally:
                connection.close()

        # 2. Run simultaneous execution in parallel threads
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(attempt_booking, link1.token)
            future2 = executor.submit(attempt_booking, link2.token)
            results.append(future1.result())
            results.append(future2.result())

        statuses = [r[0] for r in results]

        # 3. Assert strict ACID and concurrency guarantees
        assert "SUCCESS" in statuses, f"Expected one successful booking, got {results}"
        assert "CONFLICT" in statuses, f"Expected one conflict collision, got {results}"
        assert statuses.count("SUCCESS") == 1
        assert statuses.count("CONFLICT") == 1

        # 4. Assert PostgreSQL database state integrity
        active_bookings_count = Booking.objects.filter(
            starts_at=target_slot,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            is_deleted=False,
        ).count()
        assert active_bookings_count == 1, f"Expected exactly 1 booking in DB, found {active_bookings_count}"

    def test_simultaneous_overlapping_ranges_race_condition(
        self, mock_delay, admin_user, portrait_service, weekly_schedule
    ):
        """
        Tests two concurrent bookings with overlapping intervals (14:00-15:00 vs 14:30-15:30).
        """
        cust1 = Customer.objects.create(display_name="Overlap Alice")
        lead1 = Lead.objects.create(customer=cust1, source_channel="INSTAGRAM", service=portrait_service)
        link1 = BookingLinkService.create_for_lead(lead=lead1, service=portrait_service)

        cust2 = Customer.objects.create(display_name="Overlap Bob")
        lead2 = Lead.objects.create(customer=cust2, source_channel="WHATSAPP", service=portrait_service)
        link2 = BookingLinkService.create_for_lead(lead=lead2, service=portrait_service)

        target_date = date(2026, 8, 10)  # Monday
        tz = AvailabilityService.get_studio_timezone()
        slot1 = timezone.make_aware(datetime.combine(target_date, time(14, 0)), tz)
        slot2 = timezone.make_aware(datetime.combine(target_date, time(14, 30)), tz)

        results = []

        def attempt_booking(token: str, slot_time):
            connection.close()
            try:
                booking = BookingService.create_booking(
                    booking_link_token=token,
                    starts_at=slot_time,
                )
                return ("SUCCESS", str(booking.id))
            except SlotConflictError as err:
                return ("CONFLICT", str(err))
            except Exception as exc:
                return ("ERROR", str(exc))
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(attempt_booking, link1.token, slot1)
            future2 = executor.submit(attempt_booking, link2.token, slot2)
            results.append(future1.result())
            results.append(future2.result())

        statuses = [r[0] for r in results]
        assert "SUCCESS" in statuses
        assert "CONFLICT" in statuses
        assert statuses.count("SUCCESS") == 1
        assert statuses.count("CONFLICT") == 1

        active_count = Booking.objects.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            is_deleted=False,
        ).count()
        assert active_count == 1
