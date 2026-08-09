"""
Message formatters for various domain notification types.
Generates human-friendly, professional copy for customer communications.
"""
from typing import Any, Dict


class NotificationFormatter:
    """
    Renders standardized message bodies based on notification type and context variables.
    """

    @classmethod
    def format(cls, notification_type: str, context: Dict[str, Any], channel: str = "WHATSAPP") -> str:
        name = context.get("customer_name") or "Valued Client"
        service = context.get("service_name") or "Photo Shoot"
        url = context.get("booking_url") or ""
        time_str = context.get("start_time") or context.get("starts_at") or "your scheduled time"
        duration = context.get("duration_minutes") or 60
        location = context.get("studio_address") or "Photo Studio Main Branch"
        reason = context.get("cancellation_reason") or "Schedule adjustment requested"

        if notification_type == "BOOKING_LINK":
            return (
                f"Hello {name}!\n\n"
                f"Here is your private booking link for your {service}:\n"
                f"{url}\n\n"
                f"Please choose your preferred date and time to reserve your appointment."
            )

        elif notification_type == "BOOKING_CONFIRMATION":
            return (
                f"Hello {name}!\n\n"
                f"Your photo session for {service} is CONFIRMED for {time_str}.\n\n"
                f"Location: {location}\n"
                f"Duration: {duration} minutes\n\n"
                f"We look forward to creating beautiful memories with you!"
            )

        elif notification_type == "BOOKING_REMINDER":
            return (
                f"Friendly reminder, {name}!\n\n"
                f"Your upcoming {service} photo session is tomorrow at {time_str}.\n"
                f"Location: {location}\n\n"
                f"Please arrive 10 minutes early. Let us know if you have any questions!"
            )

        elif notification_type == "BOOKING_CANCELLATION":
            reschedule_msg = f"\n\nIf you'd like to reschedule, visit: {url}" if url else ""
            return (
                f"Hello {name},\n\n"
                f"Your booking for {service} on {time_str} has been cancelled.\n"
                f"Reason: {reason}{reschedule_msg}"
            )

        # Fallback to direct message or text provided in context
        return context.get("text") or context.get("message") or f"Notification for {service}"
