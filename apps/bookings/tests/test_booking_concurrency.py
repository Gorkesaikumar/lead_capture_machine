import concurrent.futures
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.test import TransactionTestCase
from django.test import TransactionTestCase
from django.utils import timezone
from apps.bookings.models import Booking, BookingLink
from apps.bookings.services import BookingService, SlotConflictError, BookingValidationError
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.services.models import PhotographyService
from apps.scheduling.models import WeeklyAvailability

from unittest.mock import patch

@patch("apps.bookings.tasks.send_booking_confirmation_whatsapp.delay")
class BookingConcurrencyTests(TransactionTestCase):
    """
    Tests asserting that PostgreSQL Exclusion Constraints and select_for_update 
    properly prevent double-booking race conditions.
    Using TransactionTestCase because we need to test real database transaction boundaries 
    and threading which requires actual commits, not just savepoints.
    """

    def setUp(self):
        self.customer = Customer.objects.create(
            display_name="Concurrency Test User",
            primary_phone="+1234567890",
        )
        self.lead = Lead.objects.create(
            customer=self.customer,
            status=Lead.Status.NEW,
        )
        self.service = PhotographyService.objects.create(
            name="Race Condition Service",
            base_price=500,
            duration_minutes=60,
            buffer_before_minutes=15,
            buffer_after_minutes=15,
            is_active=True,
        )
        # Ensure the studio is open when we try to book
        WeeklyAvailability.objects.create(
            weekday=timezone.now().weekday(),
            start_time="00:00:00",
            end_time="23:59:59",
            is_active=True,
        )

        studio_tz = ZoneInfo(getattr(settings, "TIME_ZONE", "UTC"))
        self.target_time = timezone.now().astimezone(studio_tz).replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=7)
        if self.target_time.weekday() != timezone.now().weekday():
            WeeklyAvailability.objects.create(
                weekday=self.target_time.weekday(),
                start_time="00:00:00",
                end_time="23:59:59",
                is_active=True,
            )

    def test_concurrent_slot_booking_by_different_links(self, mock_delay):
        """
        Scenario: Two DIFFERENT customers with DIFFERENT booking links try to book 
        the exact same time slot simultaneously.
        Result: One succeeds, one fails with SlotConflictError due to ExclusionConstraint.
        """
        customer2 = Customer.objects.create(
            display_name="Concurrency Test User 2",
            primary_phone="+1234567891",
        )
        lead2 = Lead.objects.create(customer=customer2, status=Lead.Status.NEW)
        
        link1 = BookingLink.objects.create(
            lead=self.lead,
            service=self.service,
            expires_at=timezone.now() + timedelta(days=7),
        )
        link2 = BookingLink.objects.create(
            lead=lead2,
            service=self.service,
            expires_at=timezone.now() + timedelta(days=7),
        )

        def attempt_booking(token):
            # We must handle database connection per thread if needed, but in Django tests
            # TransactionTestCase handles threading differently. For true concurrency testing, 
            # we just catch the exception.
            try:
                BookingService.create_booking(
                    booking_link_token=token,
                    starts_at=self.target_time,
                    service=self.service,
                )
                return True
            except SlotConflictError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(attempt_booking, link1.token)
            future2 = executor.submit(attempt_booking, link2.token)
            
            results = [future1.result(), future2.result()]

        # Exactly one should succeed, exactly one should fail
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)
        self.assertEqual(Booking.objects.count(), 1)

    def test_concurrent_double_click_same_link(self, mock_delay):
        """
        Scenario: The SAME customer double clicks "Confirm" or sends two rapid requests 
        with the SAME booking link.
        Result: One succeeds, the other fails with BookingValidationError (Link Already Used) 
        due to select_for_update lock.
        """
        link = BookingLink.objects.create(
            lead=self.lead,
            service=self.service,
            expires_at=timezone.now() + timedelta(days=7),
        )

        def attempt_booking(token):
            try:
                BookingService.create_booking(
                    booking_link_token=token,
                    starts_at=self.target_time,
                    service=self.service,
                )
                return "SUCCESS"
            except BookingValidationError as e:
                return f"VALIDATION_ERROR: {str(e)}"
            except SlotConflictError:
                return "SLOT_CONFLICT"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(attempt_booking, link.token)
            future2 = executor.submit(attempt_booking, link.token)
            
            results = [future1.result(), future2.result()]

        self.assertIn("SUCCESS", results)
        self.assertTrue(any("already been used" in res for res in results))
        self.assertEqual(Booking.objects.count(), 1)
