from django.db.models import Case, When
"""
Lead detection and lifecycle management services.
Evaluates configurable triggers on inbound messages and manages sales opportunities.
"""
import logging
import re
import regex
from typing import Any, Dict, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import AuditService
from apps.conversations.models import Message
from apps.leads.models import Lead, LeadActivity, LeadTrigger
from apps.core.realtime import broadcast_lead_updated
from apps.core.logging import PipelineLogger, PipelineStage

logger = logging.getLogger("apps.leads")


class LeadDetectionService:
    """
    Evaluates incoming normalized customer messages against active LeadTriggers.
    Creates or updates sales opportunity leads without spamming duplicate leads.
    """

    @classmethod
    def process_inbound_message(
        cls,
        message: Message,
        plog: Optional[PipelineLogger] = None,
    ) -> Tuple[Optional[Lead], bool, Optional[LeadTrigger]]:
        """
        Processes a normalized inbound message to detect lead intent.

        Rules:
        1. Normalizes message text.
        2. Evaluates active triggers (EXACT, CONTAINS, REGEX).
        3. If trigger matches, checks if customer already has an active sales opportunity.
        4. If active lead exists, attaches the message as a LeadActivity (no duplicate lead).
        5. If no active lead exists, creates a new Lead opportunity with LeadActivity.

        Returns:
            Tuple[Optional[Lead], bool, Optional[LeadTrigger]]: (Lead instance or None, created boolean, matched LeadTrigger or None)
        """
        _log = plog or PipelineLogger(base_logger=logger)
        _log.info(
            PipelineStage.LEAD_DETECTION,
            "Running lead trigger evaluation",
            message_id=str(message.id),
            external_message_id=str(message.external_message_id or ""),
            has_text=bool(message.text),
        )
        if not message.text:
            _log.debug(PipelineStage.LEAD_DETECTION, "Message has no text — skipping lead detection")
            return None, False, None

        normalized_text = cls._normalize_text(message.text)
        if not normalized_text:
            return None, False, None

        customer = message.conversation.customer
        channel = message.conversation.channel

        from django.db import IntegrityError

        # Find existing active lead for this customer
        active_lead = (
            Lead.objects.filter(
                customer=customer,
                status__in=Lead.ACTIVE_STATUSES,
                is_deleted=False,
            )
            .select_related("customer", "service", "assigned_staff")
            .order_by("-created_at")
            .first()
        )

        matched_trigger = cls._find_matching_trigger(raw_text=message.text, normalized_text=normalized_text, organization=message.conversation.organization)
        if not matched_trigger:
            _log.debug(
                PipelineStage.LEAD_DETECTION,
                "No lead trigger matched",
                message_id=str(message.id),
            )
            if active_lead:
                # Still link conversation and record activity for active lead
                with transaction.atomic():
                    updated_fields = ["updated_at"]
                    if not message.conversation.lead:
                        message.conversation.lead = active_lead
                        message.conversation.save(update_fields=["lead", "updated_at"])
                    active_lead.save(update_fields=updated_fields)

                    LeadActivity.objects.create(
                        lead=active_lead,
                        activity_type=LeadActivity.ActivityType.MESSAGE_ATTACHED,
                        message=message,
                        description="Customer sent a follow-up message",
                        metadata={
                            "message_snippet": message.text[:150],
                        },
                    )
                return active_lead, False, None
            return None, False, None

        _log.info(
            PipelineStage.LEAD_DETECTION,
            "Lead trigger matched",
            message_id=str(message.id),
            trigger_id=str(matched_trigger.id),
            trigger_phrase=matched_trigger.phrase,
            match_type=matched_trigger.match_type,
            customer_id=str(customer.id),
            has_active_lead=bool(active_lead),
        )

        if not active_lead:
            try:
                with transaction.atomic():
                    from apps.subscriptions.services import SubscriptionEntitlementService, QuotaExceededException
                    try:
                        SubscriptionEntitlementService.check_and_consume_lead_quota(
                            organization=message.conversation.organization,
                            channel=channel
                        )
                    except QuotaExceededException as quota_err:
                        _log.warning(
                            PipelineStage.LEAD_DETECTION,
                            f"Lead creation blocked due to quota limit: {quota_err}",
                            message_id=str(message.id),
                        )
                        return None, False, None

                    # Create new sales opportunity lead
                    new_lead = Lead.objects.create(
                        organization=message.conversation.organization,
                        customer=customer,
                        source_channel=channel,
                        originating_message=message,
                        service=matched_trigger.service,
                        trigger=matched_trigger,
                        status=Lead.Status.NEW,
                        priority=matched_trigger.priority,
                        summary=f"Inquiry for {matched_trigger.phrase}"[:255],
                    )

                    message.conversation.lead = new_lead
                    message.conversation.save(update_fields=["lead", "updated_at"])

                    LeadActivity.objects.create(
                        lead=new_lead,
                        activity_type=LeadActivity.ActivityType.LEAD_CREATED,
                        message=message,
                        description=(
                            f"Lead automatically created via trigger '{matched_trigger.phrase}' "
                            f"on {message.conversation.get_channel_display()}"
                        ),
                        metadata={
                            "trigger_id": str(matched_trigger.id),
                            "trigger_phrase": matched_trigger.phrase,
                            "match_type": matched_trigger.match_type,
                            "initial_message": message.text[:150],
                        },
                    )

                    logger.info(
                        "Created new lead id=%s via trigger id=%s for customer id=%s",
                        new_lead.id,
                        matched_trigger.id,
                        customer.id,
                    )
                    return new_lead, True, matched_trigger
            except IntegrityError:
                # Concurrency: another thread just created an active lead.
                # Fall back to retrieving that active lead.
                active_lead = (
                    Lead.objects.filter(
                        customer=customer,
                        status__in=Lead.ACTIVE_STATUSES,
                        is_deleted=False,
                    )
                    .select_related("customer", "service", "assigned_staff")
                    .order_by("-created_at")
                    .first()
                )
                if not active_lead:
                    raise RuntimeError("Lead concurrency fallback failed: Active lead not found.")

        # Deduplication: attach message to the existing active opportunity
        with transaction.atomic():
            updated_fields = ["updated_at"]
            if not active_lead.service and matched_trigger.service:
                active_lead.service = matched_trigger.service
                updated_fields.append("service")

            active_lead.save(update_fields=updated_fields)

            LeadActivity.objects.create(
                lead=active_lead,
                activity_type=LeadActivity.ActivityType.MESSAGE_ATTACHED,
                message=message,
                description=f"Additional customer message matched trigger '{matched_trigger.phrase}'",
                metadata={
                    "trigger_id": str(matched_trigger.id),
                    "trigger_phrase": matched_trigger.phrase,
                    "match_type": matched_trigger.match_type,
                    "message_snippet": message.text[:150],
                },
            )

            logger.info(
                "Attached message id=%s to existing active lead id=%s for customer id=%s",
                message.id,
                active_lead.id,
                customer.id,
            )
            return active_lead, False, matched_trigger

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Converts text to lower-case and strips excess whitespace/punctuation."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    @classmethod
    def _find_matching_trigger(cls, raw_text: str, normalized_text: str, organization=None) -> Optional[LeadTrigger]:
        """Evaluates active triggers in descending priority order."""
        active_triggers = (
            LeadTrigger.objects.filter(is_active=True, organization=organization)
            .select_related("service")
            .order_by(
                Case(
                    *[When(priority=p, then=i) for i, p in enumerate(["URGENT", "HIGH", "MEDIUM", "LOW"])], default=4
                ), "phrase"
            )
        )

        for trigger in active_triggers:
            phrase_norm = cls._normalize_text(trigger.phrase)
            if not phrase_norm and trigger.match_type != LeadTrigger.MatchType.REGEX:
                continue

            if trigger.match_type == LeadTrigger.MatchType.EXACT:
                if normalized_text == phrase_norm:
                    return trigger
            elif trigger.match_type == LeadTrigger.MatchType.CONTAINS:
                try:
                    pattern = r'\b' + re.escape(phrase_norm) + r'\b'
                    if re.search(pattern, normalized_text):
                        return trigger
                    
                    raw_pattern = r'\b' + re.escape(trigger.phrase.lower()) + r'\b'
                    if re.search(raw_pattern, raw_text.lower()):
                        return trigger
                except re.error:
                    pass
            elif trigger.match_type == LeadTrigger.MatchType.REGEX:
                try:
                    if regex.search(trigger.phrase, raw_text[:4096], regex.IGNORECASE, timeout=0.025):
                        return trigger
                except (regex.error, TimeoutError):
                    logger.warning("Invalid or timed-out regex trigger id=%s", trigger.id)

        return None


class LeadManagementService:
    """
    Manages lead status updates, staff assignment, and audit logs.
    """

    @classmethod
    def update_status(
        cls,
        lead: Lead,
        new_status: str,
        actor: Optional[User] = None,
        notes: Optional[str] = None,
    ) -> Lead:
        """
        Updates the status of a lead, sets lifecycle timestamps, and logs an activity.
        """
        if new_status not in Lead.Status.values:
            raise ValueError(f"Invalid lead status: {new_status}")

        old_status = lead.status
        if old_status == new_status:
            return lead

        now = timezone.now()
        lead.status = new_status
        update_fields = ["status", "updated_at"]

        if new_status == Lead.Status.QUALIFIED and not lead.qualified_at:
            lead.qualified_at = now
            update_fields.append("qualified_at")

        if new_status in Lead.TERMINAL_STATUSES and not lead.closed_at:
            lead.closed_at = now
            update_fields.append("closed_at")

        if notes:
            lead.notes = notes
            update_fields.append("notes")

        with transaction.atomic():
            lead.save(update_fields=update_fields)

            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.STATUS_CHANGED,
                actor=actor,
                description=f"Status changed from {old_status} to {new_status}",
                metadata={"old_status": old_status, "new_status": new_status, "notes": notes or ""},
            )

            AuditService.record_lead_status_changed(
                lead=lead,
                old_status=old_status,
                new_status=new_status,
                actor=actor,
                notes=notes,
            )

        broadcast_lead_updated(lead)
        logger.info("Updated lead id=%s status: %s -> %s by actor=%s", lead.id, old_status, new_status, actor)
        return lead

    @classmethod
    def assign_staff(
        cls,
        lead: Lead,
        staff: Optional[User],
        actor: Optional[User] = None,
    ) -> Lead:
        """
        Assigns a staff member/admin to the lead opportunity and logs an activity.
        """
        old_staff_name = lead.assigned_staff.email if lead.assigned_staff else "None"
        new_staff_name = staff.email if staff else "Unassigned"

        old_staff_user = lead.assigned_staff
        with transaction.atomic():
            lead.assigned_staff = staff
            lead.save(update_fields=["assigned_staff", "updated_at"])

            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.STAFF_ASSIGNED,
                actor=actor,
                description=f"Lead assigned to {new_staff_name} (was {old_staff_name})",
                metadata={
                    "old_staff_id": str(old_staff_user.id) if old_staff_user else None,
                    "new_staff_id": str(staff.id) if staff else None,
                },
            )

            AuditService.record_lead_assigned(
                lead=lead,
                old_staff=old_staff_user,
                new_staff=staff,
                actor=actor,
            )

        broadcast_lead_updated(lead)
        logger.info("Assigned lead id=%s to staff=%s by actor=%s", lead.id, new_staff_name, actor)
        return lead

    @classmethod
    def add_note(
        cls,
        lead: Lead,
        note_text: str,
        actor: Optional[User] = None,
    ) -> LeadActivity:
        """
        Adds a note to the lead audit trail.
        """
        with transaction.atomic():
            activity = LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.NOTE_ADDED,
                actor=actor,
                description=note_text,
            )
        return activity

    @classmethod
    def create_direct_lead(
        cls,
        organization: "Organization",
        source_channel: str,
        customer_name: str,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        summary: str = "",
        notes: str = "",
        tags: Optional[list] = None,
        source_identifier: str = "",
        actor: Optional[User] = None,
    ) -> Lead:
        """
        Creates a lead from a manual or website entry, resolving deduplication via CustomerResolutionService.
        """
        from apps.customers.services import CustomerResolutionService

        with transaction.atomic():
            from apps.organizations.models import Organization
            Organization.objects.select_for_update().get(pk=organization.pk)
            customer, created = CustomerResolutionService.resolve_direct_customer(
                organization=organization,
                display_name=customer_name,
                phone_number=phone_number,
                email=email
            )

            # Check if an active lead already exists for this customer
            active_lead = Lead.objects.filter(
                organization=organization,
                customer=customer,
                status__in=Lead.ACTIVE_STATUSES,
                is_deleted=False
            ).first()

            if active_lead:
                if notes:
                    existing_notes = active_lead.notes or ""
                    active_lead.notes = f"{existing_notes}\n\n[{source_channel} Submission]: {notes}".strip()
                    active_lead.save(update_fields=["notes", "updated_at"])

                LeadActivity.objects.create(
                    lead=active_lead,
                    activity_type=LeadActivity.ActivityType.NOTE_ADDED,
                    actor=actor,
                    description=f"Additional inquiry submitted via {source_channel}",
                    metadata={"summary": summary, "source_identifier": source_identifier}
                )

                broadcast_lead_updated(active_lead)
                logger.info("Updated existing active lead id=%s for customer id=%s", active_lead.id, customer.id)
                return active_lead

            # Enforce lead quota limit for direct / website form submissions
            from apps.subscriptions.services import SubscriptionEntitlementService
            SubscriptionEntitlementService.check_and_consume_lead_quota(
                organization=organization,
                channel=source_channel
            )

            lead = Lead.objects.create(
                organization=organization,
                customer=customer,
                source_channel=source_channel,
                summary=summary,
                notes=notes,
                tags=tags or [],
                source_identifier=source_identifier,
                status=Lead.Status.NEW,
                priority=Lead.Priority.MEDIUM,
                assigned_staff=actor if actor else None
            )

            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.LEAD_CREATED,
                actor=actor,
                description=f"Lead created directly via {source_channel}",
                metadata={"created_customer": created}
            )

            broadcast_lead_updated(lead)
            logger.info("Created direct lead id=%s for customer id=%s", lead.id, customer.id)
            return lead
