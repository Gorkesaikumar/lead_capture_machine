"""
Availability calculation engine for Photo Studio.
Dynamically computes available start times on the fly without pre-creating millions of slot rows.
"""
from datetime import date, datetime, time, timedelta
import logging
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from apps.bookings.models import Booking
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability
from apps.services.models import Package, PhotographyService

logger = logging.getLogger("apps.scheduling")


class AvailabilityService:
    """
    Calculates advisory appointment start times based on:
    - Recurring weekly business hours (multiple windows per day / breaks)
    - Date-specific special availability overrides
    - Full-day holiday / studio closures
    - Service duration & package duration overrides
    - Preparation buffer before & cleanup buffer after
    - Blocked periods (all-studio and service-specific)
    - Existing confirmed and reserved bookings (including booking buffers)
    - Timezone-aware bounds
    """

    @classmethod
    def get_studio_timezone(cls, organization=None) -> ZoneInfo:
        """Returns the studio's configured zoneinfo timezone."""
        tz_name = getattr(organization, "timezone", None) or getattr(settings, "TIME_ZONE", "UTC")
        return ZoneInfo(tz_name)

    @classmethod
    def get_available_slots(
        cls,
        service: PhotographyService,
        target_date: date,
        package: Optional[Package] = None,
        slot_step_minutes: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Computes all valid appointment start times for a given service on a single date.
        """
        studio_tz = cls.get_studio_timezone(service.organization)
        now_dt = timezone.now().astimezone(studio_tz)

        # 1. Check Holiday / Studio Closure
        if HolidayClosure.objects.filter(organization=service.organization, date=target_date, is_active=True).exists():
            logger.debug("Studio closed on %s due to holiday closure", target_date)
            return []

        # 2. Determine Service Durations and Buffers
        duration_minutes = package.effective_duration_minutes if package else service.duration_minutes
        buffer_before = service.buffer_before_minutes
        buffer_after = service.buffer_after_minutes

        session_delta = timedelta(minutes=duration_minutes)
        buffer_before_delta = timedelta(minutes=buffer_before)
        buffer_after_delta = timedelta(minutes=buffer_after)

        # 3. Determine Operating Windows for the Target Date
        special_availabilities = SpecialAvailability.objects.filter(organization=service.organization,
            date=target_date, is_active=True
        ).order_by("start_time")

        if special_availabilities.exists():
            operating_windows = [
                (spec.start_time, spec.end_time) for spec in special_availabilities
            ]
        else:
            weekly_availabilities = WeeklyAvailability.objects.filter(organization=service.organization,
                weekday=target_date.weekday(), is_active=True
            ).order_by("start_time")
            operating_windows = [
                (w.start_time, w.end_time) for w in weekly_availabilities
            ]

        if not operating_windows:
            logger.debug("No operating hours configured for date %s (weekday=%s)", target_date, target_date.weekday())
            return []

        # 4. Determine Day Range for Querying Busy Intervals
        day_start_dt = timezone.make_aware(datetime.combine(target_date, time.min), studio_tz)
        day_end_dt = timezone.make_aware(datetime.combine(target_date, time.max), studio_tz)

        # Query busy intervals from BlockedPeriod
        blocked_qs = BlockedPeriod.objects.filter(organization=service.organization,
            is_active=True,
            starts_at__lt=day_end_dt + timedelta(hours=6),
            ends_at__gt=day_start_dt - timedelta(hours=6),
        ).filter(Q(service__isnull=True) | Q(service=service))

        busy_intervals = [(b.starts_at, b.ends_at) for b in blocked_qs]

        # Query busy intervals from confirmed/reserved Bookings
        booking_qs = Booking.objects.filter(customer__organization=service.organization,
            is_deleted=False,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING],
            starts_at__lt=day_end_dt + timedelta(hours=6),
            ends_at__gt=day_start_dt - timedelta(hours=6),
        )

        for b in booking_qs:
            busy_intervals.append((b.blocked_starts_at, b.blocked_ends_at))

        # 5. Slide Candidate Slots across Each Operating Window
        slots = []
        step_delta = timedelta(minutes=slot_step_minutes)

        for win_start_time, win_end_time in operating_windows:
            win_start_dt = timezone.make_aware(datetime.combine(target_date, win_start_time), studio_tz)
            win_end_dt = timezone.make_aware(datetime.combine(target_date, win_end_time), studio_tz)

            curr_start = win_start_dt

            while curr_start + session_delta <= win_end_dt:
                cand_start = curr_start
                cand_end = cand_start + session_delta
                req_block_start = cand_start - buffer_before_delta
                req_block_end = cand_end + buffer_after_delta

                # Validate candidate session + preparation & cleanup buffers fit inside operating window
                if req_block_start >= win_start_dt and req_block_end <= win_end_dt:
                    # Filter out past times if target_date is today or in the past
                    if cand_start > now_dt:
                        # Check collision: interval overlap if max(A, C) < min(B, D)
                        has_collision = False
                        for busy_start, busy_end in busy_intervals:
                            if max(req_block_start, busy_start) < min(req_block_end, busy_end):
                                has_collision = True
                                break

                        if not has_collision:
                            slots.append({
                                "starts_at": cand_start.isoformat(),
                                "ends_at": cand_end.isoformat(),
                                "duration_minutes": duration_minutes,
                                "buffer_before_minutes": buffer_before,
                                "buffer_after_minutes": buffer_after,
                            })

                curr_start += step_delta

        return slots

    @classmethod
    def get_range_availability(
        cls,
        service: PhotographyService,
        start_date: date,
        end_date: date,
        package: Optional[Package] = None,
        slot_step_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        Computes availability across a date range (up to 31 days).
        """
        if (end_date - start_date).days > 31:
            raise ValueError("Availability range cannot exceed 31 days.")
        if end_date < start_date:
            raise ValueError("End date must be on or after start date.")

        studio_tz = cls.get_studio_timezone(service.organization)
        results = []
        current_date = start_date

        while current_date <= end_date:
            daily_slots = cls.get_available_slots(
                service=service,
                target_date=current_date,
                package=package,
                slot_step_minutes=slot_step_minutes,
            )
            results.append({
                "date": current_date.isoformat(),
                "weekday": current_date.strftime("%A"),
                "is_available": len(daily_slots) > 0,
                "slots_count": len(daily_slots),
                "slots": daily_slots,
            })
            current_date += timedelta(days=1)

        return {
            "service_id": str(service.id),
            "service_name": service.name,
            "package_id": str(package.id) if package else None,
            "package_name": package.name if package else None,
            "timezone": str(studio_tz),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": results,
        }
