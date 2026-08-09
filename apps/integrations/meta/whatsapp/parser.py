"""
WhatsApp Cloud API Inbound Webhook Parser.
Transforms raw Meta WhatsApp Cloud API payloads into NormalizedInboundMessage
and WhatsAppStatusUpdate instances.
"""
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
import logging
from typing import Any, Dict, List, Optional
from apps.integrations.meta.base import InboundMessageParser, NormalizedInboundMessage

logger = logging.getLogger("apps.integrations.meta.whatsapp")


@dataclass
class WhatsAppStatusUpdate:
    """
    Represents an outbound message delivery status update sent by WhatsApp Cloud API.
    """
    external_message_id: str
    recipient_id: str
    status: str  # "sent", "delivered", "read", "failed"
    timestamp: Optional[datetime] = None
    error_details: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


class WhatsAppInboundParser(InboundMessageParser):
    """
    Parses incoming WhatsApp Cloud API webhook events (object == 'whatsapp_business_account').
    Extracts both inbound customer messages and outbound message status updates.
    """

    def can_parse(self, payload: Dict[str, Any]) -> bool:
        """
        Returns True if payload object is 'whatsapp_business_account'.
        """
        if not isinstance(payload, dict):
            return False
        return payload.get("object") == "whatsapp_business_account"

    def parse_messages(self, payload: Dict[str, Any]) -> List[NormalizedInboundMessage]:
        """
        Extracts all incoming WhatsApp customer messages from the webhook payload.
        """
        normalized_messages: List[NormalizedInboundMessage] = []

        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return normalized_messages

        for entry in entries:
            changes = entry.get("changes", [])
            if not isinstance(changes, list):
                continue

            for change in changes:
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue

                # Build a mapping of wa_id -> profile name from contacts list
                contacts_map: Dict[str, str] = {}
                contacts = value.get("contacts", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        wa_id = str(contact.get("wa_id", "")).strip()
                        profile = contact.get("profile", {})
                        name = profile.get("name")
                        if wa_id and name:
                            contacts_map[wa_id] = name

                messages = value.get("messages", [])
                if not isinstance(messages, list):
                    continue

                for msg in messages:
                    sender_wa_id = str(msg.get("from", "")).strip()
                    message_id = str(msg.get("id", "")).strip()
                    if not sender_wa_id or not message_id:
                        continue

                    sender_name = contacts_map.get(sender_wa_id)
                    msg_type = str(msg.get("type", "text")).lower()

                    text: Optional[str] = None
                    attachments_list: List[Dict[str, Any]] = []
                    normalized_type = "TEXT"

                    # Parse timestamp (WhatsApp sends string/int seconds)
                    raw_ts = msg.get("timestamp")
                    provider_ts: Optional[datetime] = None
                    if raw_ts:
                        try:
                            provider_ts = datetime.fromtimestamp(int(raw_ts), tz=dt_timezone.utc)
                        except (ValueError, OSError, TypeError):
                            provider_ts = None

                    # Extract body/media depending on message type
                    if msg_type == "text":
                        text_obj = msg.get("text", {})
                        text = text_obj.get("body", "")
                        normalized_type = "TEXT"

                    elif msg_type in ["image", "video", "audio", "document"]:
                        media_obj = msg.get(msg_type, {})
                        text = media_obj.get("caption")
                        media_id = media_obj.get("id")
                        mime_type = media_obj.get("mime_type")
                        attachments_list.append({
                            "type": msg_type.upper(),
                            "media_id": media_id,
                            "mime_type": mime_type,
                            "raw": media_obj,
                        })
                        normalized_type = "DOCUMENT" if msg_type == "document" else msg_type.upper()

                    elif msg_type == "button":
                        btn_obj = msg.get("button", {})
                        text = btn_obj.get("text", "")
                        normalized_type = "TEXT"

                    elif msg_type == "interactive":
                        interactive_obj = msg.get("interactive", {})
                        int_type = interactive_obj.get("type")
                        if int_type == "button_reply":
                            text = interactive_obj.get("button_reply", {}).get("title", "")
                        elif int_type == "list_reply":
                            text = interactive_obj.get("list_reply", {}).get("title", "")
                        normalized_type = "TEXT"

                    else:
                        normalized_type = "OTHER"
                        text = f"[{msg_type}]"

                    norm_msg = NormalizedInboundMessage(
                        channel="WHATSAPP",
                        external_message_id=message_id,
                        external_user_id=sender_wa_id,
                        sender_name=sender_name,
                        sender_username=None,
                        sender_phone=sender_wa_id,
                        text=text,
                        message_type=normalized_type,
                        attachments=attachments_list,
                        provider_timestamp=provider_ts,
                        raw_metadata=msg,
                    )
                    normalized_messages.append(norm_msg)

        logger.info(
            "Parsed %d normalized WhatsApp messages from webhook payload.",
            len(normalized_messages),
        )
        return normalized_messages

    def parse_status_updates(self, payload: Dict[str, Any]) -> List[WhatsAppStatusUpdate]:
        """
        Extracts delivery status updates (sent, delivered, read, failed) from the webhook payload.
        """
        status_updates: List[WhatsAppStatusUpdate] = []

        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return status_updates

        for entry in entries:
            changes = entry.get("changes", [])
            if not isinstance(changes, list):
                continue

            for change in changes:
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue

                statuses = value.get("statuses", [])
                if not isinstance(statuses, list):
                    continue

                for st in statuses:
                    msg_id = str(st.get("id", "")).strip()
                    status_name = str(st.get("status", "")).strip().lower()
                    recipient_id = str(st.get("recipient_id", "")).strip()

                    if not msg_id or not status_name:
                        continue

                    # Parse timestamp
                    raw_ts = st.get("timestamp")
                    ts: Optional[datetime] = None
                    if raw_ts:
                        try:
                            ts = datetime.fromtimestamp(int(raw_ts), tz=dt_timezone.utc)
                        except (ValueError, OSError, TypeError):
                            ts = None

                    # Extract error details if failed
                    errors = st.get("errors", [])
                    error_details: Optional[Dict[str, Any]] = None
                    if errors and isinstance(errors, list):
                        error_details = errors[0] if isinstance(errors[0], dict) else {"error": errors[0]}

                    status_updates.append(
                        WhatsAppStatusUpdate(
                            external_message_id=msg_id,
                            recipient_id=recipient_id,
                            status=status_name,
                            timestamp=ts,
                            error_details=error_details,
                            raw_data=st,
                        )
                    )

        if status_updates:
            logger.info("Parsed %d WhatsApp status updates from webhook payload.", len(status_updates))

        return status_updates
