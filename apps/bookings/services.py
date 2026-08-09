"""
Booking and Booking Link services with strict ACID and concurrency guarantees.
"""
from datetime import datetime, timedelta
import logging
from typing import Optional
from django.db import IntegrityError, transaction
from django.db.utils import OperationalError
from django.utils import timezone
from psycopg.types.range import Range
from apps.audit.services import AuditService
from apps.bookings.models import Booking, BookingLink
from apps.leads.models import Lead, LeadActivity
from apps.scheduling.services import AvailabilityService
from apps.services.models import Package, PhotographyService
from apps.core.realtime import (
    broadcast_booking_created,
    broadcast_booking_updated,
    broadcast_lead_updated,
)

logger = logging.getLogger("apps.bookings")


class BookingValidationError(Exception):
    """Raised when booking link or parameters are invalid."""
    pass


class SlotConflictError(Exception):
    """Raised when the requested appointment slot collides with an existing booking (HTTP 409)."""
    pass


class ScheduleUnavailableError(Exception):
    """Raised when the requested appointment is outside operating hours or during a closure."""
    pass


class BookingLinkService:
    """
    Manages generation, validation, and lifecycle of secure public booking links.
    """

    @classmethod
    def create_for_lead(
        cls,
        lead: Lead,
        service: Optional[PhotographyService] = None,
        expires_in_days: int = 7,
        created_by=None,
    ) -> BookingLink:
        """
        Creates a new cryptographically secure booking link for a sales lead.
        """
        with transaction.atomic():
            link = BookingLink.objects.create(
                lead=lead,
                service=service or lead.service,
                expires_at=timezone.now() + timedelta(days=expires_in_days),
                created_by=created_by,
            )

            # Transition lead status to BOOKING_LINK_SENT if not already booked/closed
            if lead.status in [Lead.Status.NEW, Lead.Status.CONTACTED, Lead.Status.QUALIFIED]:
                lead.status = Lead.Status.BOOKING_LINK_SENT
                lead.save(update_fields=["status", "updated_at"])

            LeadActivity.objects.create(
                lead=lead,
                actor=created_by,
                activity_type=LeadActivity.ActivityType.BOOKING_LINK_SENT,
                description=f"Generated booking link valid until {link.expires_at.strftime('%Y-%m-%d %H:%M')}",
                metadata={"booking_link_id": str(link.id), "token": link.token},
            )

            AuditService.record_booking_link_generated(
                booking_link=link,
                actor=created_by,
            )

            logger.info("Created booking link %s for lead %s", link.token[:8], lead.id)
            return link

    @classmethod
    def validate_link(cls, token: str, allow_used: bool = False) -> BookingLink:
        """
        Validates token existence, expiration, and redemption/revocation state.
        """
        try:
            link = BookingLink.objects.select_related(
                "lead", "lead__customer", "service"
            ).get(token=token)
        except BookingLink.DoesNotExist:
            raise BookingValidationError("Invalid or non-existent booking link.")

        if link.is_revoked:
            raise BookingValidationError("This booking link has been revoked.")
        if not allow_used and link.is_used:
            raise BookingValidationError("This booking link has already been used.")
        if link.expires_at <= timezone.now():
            raise BookingValidationError("This booking link has expired.")

        return link

    @classmethod
    def revoke_link(cls, booking_link_id: str, revoked_by=None) -> BookingLink:
        """
        Revokes an active booking link.
        """
        with transaction.atomic():
            link = BookingLink.objects.select_for_update().get(id=booking_link_id)
            if link.is_used:
                raise BookingValidationError("Cannot revoke an already used booking link.")

            link.is_revoked = True
            link.revoked_at = timezone.now()
            link.save(update_fields=["is_revoked", "revoked_at", "updated_at"])

            LeadActivity.objects.create(
                lead=link.lead,
                actor=revoked_by,
                activity_type=LeadActivity.ActivityType.NOTE_ADDED,
                description="Booking link was revoked by studio admin.",
                metadata={"booking_link_id": str(link.id)},
            )
            return link


class BookingService:
    """
    Handles concurrency-safe appointment scheduling with PostgreSQL exclusion enforcement.
    """

    @classmethod
    def create_booking(
        cls,
        booking_link_token: str,
        starts_at: datetime,
        service: Optional[PhotographyService] = None,
        package: Optional[Package] = None,
        customer_notes: str = "",
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: Optional[str] = None,
    ) -> Booking:
        """
        Atomically books an appointment for a customer through their secure booking link.
        Guarantees that two concurrent overlapping attempts cannot both succeed.
        """
        # Ensure starts_at is timezone-aware
        if timezone.is_naive(starts_at):
            studio_tz = AvailabilityService.get_studio_timezone()
            starts_at = timezone.make_aware(starts_at, studio_tz)

        with transaction.atomic():
            # 1. Lock and validate the BookingLink
            try:
                link = (
                    BookingLink.objects.select_for_update(of=("self",))
                    .select_related("lead", "lead__customer", "service")
                    .get(token=booking_link_token)
                )
            except BookingLink.DoesNotExist:
                raise BookingValidationError("Invalid or non-existent booking link.")

            if link.is_revoked:
                raise BookingValidationError("This booking link has been revoked.")
            if link.is_used:
                raise BookingValidationError("This booking link has already been used.")
            if link.expires_at <= timezone.now():
                raise BookingValidationError("This booking link has expired.")

            lead = link.lead
            customer = lead.customer

            # Update customer details
            customer.display_name = customer_name or customer.display_name
            customer.primary_phone = customer_phone or customer.primary_phone
            if customer_email:
                customer.email = customer_email
            customer.save(update_fields=["display_name", "primary_phone", "email", "updated_at"])

            # 2. Determine Service and Package
            effective_service = link.service or service or lead.service
            if not effective_service:
                raise BookingValidationError("A photography service must be selected.")
            if effective_service.is_deleted or not effective_service.is_active:
                raise BookingValidationError("The selected photography service is not available.")

            if package:
                if package.service_id != effective_service.id or package.is_deleted or not package.is_active:
                    raise BookingValidationError("The selected package is not valid for this service.")

            # 3. Calculate session & buffer durations
            duration_minutes = (
                package.effective_duration_minutes
                if package
                else effective_service.duration_minutes
            )
            ends_at = starts_at + timedelta(minutes=duration_minutes)
            buffer_before = effective_service.buffer_before_minutes
            buffer_after = effective_service.buffer_after_minutes
            blocked_starts_at = starts_at - timedelta(minutes=buffer_before)
            blocked_ends_at = ends_at + timedelta(minutes=buffer_after)
            blocked_time_range = Range(
                blocked_starts_at, blocked_ends_at, bounds="[)"
            )

            # 4. Validate against studio operating hours and closures
            studio_tz = AvailabilityService.get_studio_timezone()
            target_date = starts_at.astimezone(studio_tz).date()

            available_slots = AvailabilityService.get_available_slots(
                service=effective_service,
                target_date=target_date,
                package=package,
                slot_step_minutes=15,  # 15-minute granularity for precision
            )

            # Check if requested starts_at is in candidate slot start times
            starts_at_iso = starts_at.isoformat()
            matched_slot = any(s["starts_at"] == starts_at_iso for s in available_slots)

            if not matched_slot:
                # Check whether conflict is due to an existing booking vs closed studio
                overlap_exists = Booking.objects.filter(
                    is_deleted=False,
                    status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                    blocked_starts_at__lt=blocked_ends_at,
                    blocked_ends_at__gt=blocked_starts_at,
                ).exists()

                if overlap_exists:
                    raise SlotConflictError(
                        "The requested appointment slot is no longer available."
                    )
                raise ScheduleUnavailableError(
                    "The requested appointment is outside studio operating hours or during a closure."
                )

            # 5. Insert Booking record (Protected by PostgreSQL ExclusionConstraint)
            try:
                booking = Booking.objects.create(
                    customer=customer,
                    lead=lead,
                    service=effective_service,
                    package=package,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    buffer_before_minutes=buffer_before,
                    buffer_after_minutes=buffer_after,
                    blocked_starts_at=blocked_starts_at,
                    blocked_ends_at=blocked_ends_at,
                    blocked_time_range=blocked_time_range,
                    status=Booking.Status.CONFIRMED,
                    customer_notes=customer_notes,
                    booked_at=timezone.now(),
                )
            except (IntegrityError, OperationalError) as exc:
                logger.warning(
                    "PostgreSQL ExclusionConstraint caught slot collision for %s (%s to %s): %s",
                    effective_service.name,
                    starts_at,
                    ends_at,
                    exc,
                )
                raise SlotConflictError(
                    "The requested appointment slot has just been booked by another customer."
                )

            # 6. Update Booking Link State
            link.is_used = True
            link.used_at = timezone.now()
            link.save(update_fields=["is_used", "used_at", "updated_at"])

            # 7. Update Lead State to BOOKED
            lead.status = Lead.Status.BOOKED
            lead.service = effective_service
            lead.closed_at = timezone.now()
            lead.save(update_fields=["status", "service", "closed_at", "updated_at"])

            # 8. Record Lead Activity
            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.STATUS_CHANGED,
                description=(
                    f"Appointment booked for {starts_at.strftime('%Y-%m-%d %H:%M')} "
                    f"({effective_service.name}{f' - {package.name}' if package else ''})"
                ),
                metadata={
                    "booking_id": str(booking.id),
                    "service_id": str(effective_service.id),
                    "starts_at": starts_at.isoformat(),
                    "ends_at": ends_at.isoformat(),
                },
            )

            AuditService.record_booking_created(
                booking=booking,
                actor=link.created_by if hasattr(link, "created_by") else None,
            )

            logger.info(
                "Successfully created booking %s for customer %s (service: %s, starts: %s)",
                booking.id,
                customer.display_name,
                effective_service.name,
                starts_at,
            )
            
            # Queue WhatsApp Confirmation
            from apps.bookings.tasks import send_booking_confirmation_whatsapp
            transaction.on_commit(lambda: send_booking_confirmation_whatsapp.delay(str(booking.id)))
            
            # Broadcast real-time booking event to admin dashboard
            broadcast_booking_created(booking)
            if lead:
                broadcast_lead_updated(lead)

            return booking

    @classmethod
    def cancel_booking(
        cls,
        booking: Booking,
        reason: str = "",
        internal_notes: str = "",
        cancelled_by=None,
    ) -> Booking:
        """
        Cancels an appointment, freeing the slot for future bookings.
        """
        if booking.status == Booking.Status.CANCELLED:
            raise BookingValidationError("This booking is already cancelled.")
        if booking.status == Booking.Status.COMPLETED:
            raise BookingValidationError("Cannot cancel a completed booking.")

        with transaction.atomic():
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = timezone.now()
            if internal_notes:
                booking.internal_notes = (
                    f"{booking.internal_notes}\n[Cancelled]: {internal_notes}".strip()
                )
            booking.save(
                update_fields=["status", "cancelled_at", "internal_notes", "updated_at"]
            )

            if booking.lead:
                LeadActivity.objects.create(
                    lead=booking.lead,
                    actor=cancelled_by,
                    activity_type=LeadActivity.ActivityType.STATUS_CHANGED,
                    description=f"Booking cancelled: {reason or 'No reason provided'}",
                    metadata={"booking_id": str(booking.id), "reason": reason},
                )

            AuditService.record_booking_cancelled(
                booking=booking,
                reason=reason,
                actor=cancelled_by,
            )

            broadcast_booking_updated(booking)
            if booking.lead:
                broadcast_lead_updated(booking.lead)

            logger.info("Cancelled booking %s (reason: %s)", booking.id, reason)
            return booking
