"""
Audit logging service for tracking administrative, security, and domain events.
Includes automatic secret redaction, IP extraction, and immutable persistence.
"""
from datetime import date, datetime
import logging
from typing import Any, Dict, List, Optional, Set, Union
import uuid
from django.db import models, transaction
from apps.audit.models import AuditEvent

logger = logging.getLogger("apps.audit")

SENSITIVE_KEY_PATTERNS: Set[str] = {
    "password",
    "secret",
    "token",
    "access_token",
    "app_secret",
    "verify_token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credentials",
    "credential",
    "private_key",
    "secret_key",
    "credit_card",
    "cvv",
    "card_number",
    "ssn",
    "pin",
}


def sanitize_value(val: Any) -> Any:
    """
    Converts arbitrary objects into JSON-serializable primitives.
    """
    if isinstance(val, (uuid.UUID,)):
        return str(val)
    elif isinstance(val, (datetime, date)):
        return val.isoformat()
    elif isinstance(val, models.Model):
        return f"{val.__class__.__name__}(pk={val.pk})"
    elif isinstance(val, dict):
        return sanitize_metadata(val)
    elif isinstance(val, (list, tuple, set)):
        return [sanitize_value(item) for item in val]
    return val


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recursively redacts sensitive keys such as passwords, tokens, API keys, and secrets.
    """
    if not metadata or not isinstance(metadata, dict):
        return {}

    cleaned: Dict[str, Any] = {}
    for k, v in metadata.items():
        key_str = str(k).lower().strip()
        is_sensitive = any(pattern in key_str for pattern in SENSITIVE_KEY_PATTERNS)

        if is_sensitive:
            cleaned[str(k)] = "[REDACTED]"
        elif isinstance(v, dict):
            cleaned[str(k)] = sanitize_metadata(v)
        elif isinstance(v, (list, tuple, set)):
            cleaned[str(k)] = [
                sanitize_metadata(item) if isinstance(item, dict) else sanitize_value(item)
                for item in v
            ]
        else:
            cleaned[str(k)] = sanitize_value(v)

    return cleaned


class AuditService:
    """
    Centralized auditing service for the photo studio platform.
    """

    @classmethod
    def extract_client_ip(cls, request: Any) -> Optional[str]:
        """
        Extracts client IP address from HttpRequest headers or remote address.
        """
        if not request:
            return None

        # Check standard reverse proxy headers
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # First IP is client IP
            ip = x_forwarded_for.split(",")[0].strip()
            if ip:
                return ip

        remote_addr = request.META.get("REMOTE_ADDR")
        return remote_addr.strip() if remote_addr else None

    @classmethod
    def record_event(
        cls,
        action: str,
        entity_type: str,
        entity_id: Any,
        actor: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        """
        Atomically records an immutable audit event with sanitized metadata.

        Args:
            action: Standardized action code (from AuditEvent.Action or custom).
            entity_type: Name of the domain entity class (e.g. Lead, Booking).
            entity_id: Primary key or identifier of the entity.
            actor: User who triggered the action (optional).
            metadata: Contextual data and diffs.
            ip_address: Client IP address (optional).
            request: HttpRequest object (used to extract actor and IP if omitted).

        Returns:
            AuditEvent: Newly created immutable audit record.
        """
        # Resolve actor from request if omitted
        resolved_actor = actor
        if resolved_actor is None and request and hasattr(request, "user"):
            user = request.user
            if user and user.is_authenticated:
                resolved_actor = user

        # Resolve IP address from request if omitted
        resolved_ip = ip_address
        if not resolved_ip and request:
            resolved_ip = cls.extract_client_ip(request)

        # Normalize entity_id
        entity_id_str = str(entity_id) if entity_id is not None else ""

        # Sanitize metadata to strip passwords, tokens, and secrets
        cleaned_metadata = sanitize_metadata(metadata)

        try:
            event = AuditEvent.objects.create(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id_str,
                actor=resolved_actor,
                metadata=cleaned_metadata,
                ip_address=resolved_ip,
            )
            logger.info(
                "Recorded AuditEvent id=%s action=%s entity=%s:%s actor=%s ip=%s",
                event.id,
                action,
                entity_type,
                entity_id_str,
                resolved_actor.email if resolved_actor else "System",
                resolved_ip,
            )
            return event
        except Exception as exc:
            logger.error(
                "Failed to record AuditEvent for action=%s entity=%s:%s: %s",
                action,
                entity_type,
                entity_id_str,
                str(exc),
                exc_info=True,
            )
            raise

    # -------------------------------------------------------------------------
    # Specialized Domain Action Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def record_lead_status_changed(
        cls,
        lead: Any,
        old_status: str,
        new_status: str,
        actor: Optional[Any] = None,
        notes: Optional[str] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.LEAD_STATUS_CHANGED,
            entity_type="Lead",
            entity_id=lead.id,
            actor=actor,
            metadata={
                "old_status": old_status,
                "new_status": new_status,
                "customer_id": str(lead.customer_id) if hasattr(lead, "customer_id") else None,
                "notes": notes or "",
            },
            request=request,
        )

    @classmethod
    def record_lead_assigned(
        cls,
        lead: Any,
        old_staff: Optional[Any],
        new_staff: Optional[Any],
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.LEAD_ASSIGNED,
            entity_type="Lead",
            entity_id=lead.id,
            actor=actor,
            metadata={
                "old_staff_id": str(old_staff.id) if old_staff else None,
                "old_staff_email": getattr(old_staff, "email", None),
                "new_staff_id": str(new_staff.id) if new_staff else None,
                "new_staff_email": getattr(new_staff, "email", None),
            },
            request=request,
        )

    @classmethod
    def record_booking_created(
        cls,
        booking: Any,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id=booking.id,
            actor=actor,
            metadata={
                "customer_id": str(booking.customer_id) if hasattr(booking, "customer_id") else None,
                "lead_id": str(booking.lead_id) if hasattr(booking, "lead_id") and booking.lead_id else None,
                "service_id": str(booking.service_id) if hasattr(booking, "service_id") and booking.service_id else None,
                "service_name": booking.service.name if hasattr(booking, "service") and booking.service else None,
                "starts_at": booking.starts_at.isoformat() if hasattr(booking, "starts_at") and booking.starts_at else None,
                "ends_at": booking.ends_at.isoformat() if hasattr(booking, "ends_at") and booking.ends_at else None,
                "status": getattr(booking, "status", None),
            },
            request=request,
        )

    @classmethod
    def record_booking_cancelled(
        cls,
        booking: Any,
        reason: Optional[str] = None,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.BOOKING_CANCELLED,
            entity_type="Booking",
            entity_id=booking.id,
            actor=actor,
            metadata={
                "customer_id": str(booking.customer_id) if hasattr(booking, "customer_id") else None,
                "reason": reason or "",
                "status": getattr(booking, "status", None),
                "cancelled_at": booking.cancelled_at.isoformat() if hasattr(booking, "cancelled_at") and booking.cancelled_at else None,
            },
            request=request,
        )

    @classmethod
    def record_availability_changed(
        cls,
        entity_type: str,
        entity_id: Any,
        change_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        meta = {"change_type": change_type}
        if metadata:
            meta.update(metadata)
        return cls.record_event(
            action=AuditEvent.Action.AVAILABILITY_CHANGED,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=meta,
            request=request,
        )

    @classmethod
    def record_service_changed(
        cls,
        entity_type: str,
        entity_id: Any,
        change_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        meta = {"change_type": change_type}
        if metadata:
            meta.update(metadata)
        return cls.record_event(
            action=AuditEvent.Action.SERVICE_CHANGED,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=meta,
            request=request,
        )

    @classmethod
    def record_booking_link_generated(
        cls,
        booking_link: Any,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.BOOKING_LINK_GENERATED,
            entity_type="BookingLink",
            entity_id=booking_link.id,
            actor=actor,
            metadata={
                "lead_id": str(booking_link.lead_id) if hasattr(booking_link, "lead_id") else None,
                "service_id": str(booking_link.service_id) if hasattr(booking_link, "service_id") and booking_link.service_id else None,
                "expires_at": booking_link.expires_at.isoformat() if hasattr(booking_link, "expires_at") and booking_link.expires_at else None,
                "link_prefix": booking_link.token[:8] if hasattr(booking_link, "token") and booking_link.token else None,
            },
            request=request,
        )

    @classmethod
    def record_booking_link_sent(
        cls,
        notification: Any,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.BOOKING_LINK_SENT,
            entity_type="Notification",
            entity_id=notification.id,
            actor=actor,
            metadata={
                "customer_id": str(notification.customer_id) if hasattr(notification, "customer_id") else None,
                "channel": getattr(notification, "channel", None),
                "notification_type": getattr(notification, "notification_type", None),
                "idempotency_key": getattr(notification, "idempotency_key", None),
            },
            request=request,
        )

    @classmethod
    def record_integration_settings_changed(
        cls,
        setting_name: str,
        old_value: Any,
        new_value: Any,
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        setting_key_lower = str(setting_name).lower()
        is_sensitive = any(pattern in setting_key_lower for pattern in SENSITIVE_KEY_PATTERNS)
        safe_old = "[REDACTED]" if is_sensitive and old_value is not None else old_value
        safe_new = "[REDACTED]" if is_sensitive and new_value is not None else new_value

        return cls.record_event(
            action=AuditEvent.Action.INTEGRATION_SETTINGS_CHANGED,
            entity_type="IntegrationSetting",
            entity_id=setting_name,
            actor=actor,
            metadata={
                "setting_name": setting_name,
                "old_value": safe_old,
                "new_value": safe_new,
            },
            request=request,
        )

    @classmethod
    def record_staff_role_changed(
        cls,
        target_user: Any,
        role_changes: Dict[str, Any],
        actor: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> AuditEvent:
        return cls.record_event(
            action=AuditEvent.Action.STAFF_ROLE_CHANGED,
            entity_type="User",
            entity_id=target_user.id,
            actor=actor,
            metadata={
                "target_email": getattr(target_user, "email", None),
                "changes": role_changes,
            },
            request=request,
        )
