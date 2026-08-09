"""
Instagram Inbound Webhook Parser.
Transforms raw Meta Instagram Messaging webhook payloads into NormalizedInboundMessage instances.
Supports text, quick replies, photo/video attachments, story mentions, and shares.
"""
from datetime import datetime, timezone as dt_timezone
import logging
from typing import Any, Dict, List, Optional
from apps.integrations.meta.base import InboundMessageParser, NormalizedInboundMessage

logger = logging.getLogger("apps.integrations.meta.instagram")


class InstagramInboundParser(InboundMessageParser):
    """
    Parses incoming Instagram webhook events (object == 'instagram').
    """

    def can_parse(self, payload: Dict[str, Any]) -> bool:
        """
        Returns True if payload object is 'instagram' or contains instagram messaging entries.
        """
        if not isinstance(payload, dict):
            return False

        # WhatsApp payloads should never be processed by the Instagram parser
        if payload.get("object") == "whatsapp_business_account":
            return False

        if payload.get("object") in ("instagram", "page"):
            return True
        entries = payload.get("entry", [])
        if isinstance(entries, list) and len(entries) > 0:
            first = entries[0]
            if isinstance(first, dict) and ("messaging" in first or "changes" in first):
                return True
        return False

    @staticmethod
    def _parse_timestamp(raw_ts: Any) -> datetime:
        """
        Safely converts raw timestamp from Meta payload to a timezone-aware UTC datetime.
        Handles:
        - 13-digit milliseconds (e.g. 1723145678000 -> divide by 1000)
        - 10-digit seconds (e.g. 1723145678)
        - Numeric strings (e.g. "1723145678000" or "1723145678")
        - ISO datetime strings
        - None / missing values (falls back to current UTC time)
        """
        from django.utils import timezone
        if not raw_ts:
            return timezone.now()

        if isinstance(raw_ts, datetime):
            if timezone.is_naive(raw_ts):
                return timezone.make_aware(raw_ts, dt_timezone.utc)
            return raw_ts

        if isinstance(raw_ts, (int, float, str)):
            try:
                ts_val = float(raw_ts)
                # If timestamp is > 1e11 (approx Sep 1973 in ms), it is in milliseconds
                if ts_val > 1e11:
                    ts_val = ts_val / 1000.0
                return datetime.fromtimestamp(ts_val, tz=dt_timezone.utc)
            except (ValueError, OSError, OverflowError):
                pass

        if isinstance(raw_ts, str):
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(raw_ts)
            if parsed:
                if timezone.is_naive(parsed):
                    return timezone.make_aware(parsed, dt_timezone.utc)
                return parsed

        return timezone.now()

    def parse_messages(self, payload: Dict[str, Any]) -> List[NormalizedInboundMessage]:
        """
        Extracts all incoming user messages from the Instagram webhook payload.
        Ignores echo messages (messages sent by the studio itself) and delivery/read receipts.
        """
        normalized_messages: List[NormalizedInboundMessage] = []

        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return normalized_messages

        for entry in entries:
            # 1. Parse legacy/standard 'messaging' array
            messaging_events = entry.get("messaging", [])
            if isinstance(messaging_events, list):
                for event in messaging_events:
                    message_obj = event.get("message")
                    if not message_obj:
                        continue

                    # Ignore echo messages sent by the page/account itself
                    if message_obj.get("is_echo", False):
                        logger.debug("Skipping Instagram echo message: %s", message_obj.get("mid"))
                        continue

                    sender = event.get("sender", {})
                    recipient = event.get("recipient", {})
                    sender_id = str(sender.get("id", "")).strip()
                    recipient_id = str(recipient.get("id", "")).strip()
                    
                    logger.info(
                        "[DIAGNOSTIC] Parsed INSTAGRAM standard message. sender.id=%s recipient.id=%s mid=%s",
                        sender_id, recipient_id, message_obj.get("mid", "")
                    )

                    if not sender_id:
                        continue

                    message_id = str(message_obj.get("mid", "")).strip()
                    text = message_obj.get("text")

                    # Handle quick reply payload if text is absent
                    quick_reply = message_obj.get("quick_reply")
                    if not text and isinstance(quick_reply, dict):
                        text = quick_reply.get("payload") or quick_reply.get("title")

                    # Parse timestamp
                    provider_ts = self._parse_timestamp(event.get("timestamp"))

                    # Parse attachments
                    attachments_list: List[Dict[str, Any]] = []
                    message_type = "TEXT"
                    raw_attachments = message_obj.get("attachments", [])
                    if isinstance(raw_attachments, list) and raw_attachments:
                        for att in raw_attachments:
                            att_type = str(att.get("type", "image")).upper()
                            payload_data = att.get("payload", {})
                            attachments_list.append({
                                "type": att_type,
                                "url": payload_data.get("url"),
                                "raw": att,
                            })
                        # Set primary message type from first attachment
                        first_type = attachments_list[0]["type"]
                        if first_type in ["IMAGE", "VIDEO", "AUDIO", "FILE"]:
                            message_type = "DOCUMENT" if first_type == "FILE" else first_type
                        elif first_type in ["STORY_MENTION", "SHARE"]:
                            message_type = "IMAGE"
                            if not text:
                                text = f"[Instagram {first_type.replace('_', ' ').title()}]"
                        else:
                            message_type = "OTHER"

                    norm_msg = NormalizedInboundMessage(
                        channel="INSTAGRAM",
                        external_message_id=message_id,
                        external_user_id=sender_id,
                        sender_name=None,
                        sender_username=None,
                        sender_phone=None,
                        text=text,
                        message_type=message_type,
                        attachments=attachments_list,
                        provider_timestamp=provider_ts,
                        raw_metadata=event,
                    )
                    normalized_messages.append(norm_msg)

            # 2. Parse Graph API / App Dashboard Test 'changes' array
            changes = entry.get("changes", [])
            if isinstance(changes, list):
                for change in changes:
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        if not isinstance(value, dict):
                            continue
                            
                        message_obj = value.get("message", {})
                        if not message_obj:
                            continue
                            
                        sender = value.get("sender", {})
                        recipient = value.get("recipient", {})
                        sender_id = str(sender.get("id", "")).strip()
                        recipient_id = str(recipient.get("id", "")).strip()
                        
                        logger.info(
                            "[DIAGNOSTIC] Parsed INSTAGRAM changes array message. sender.id=%s recipient.id=%s mid=%s",
                            sender_id, recipient_id, message_obj.get("mid", "")
                        )
                        
                        if not sender_id:
                            continue
                            
                        message_id = str(message_obj.get("mid", "")).strip()
                        text = message_obj.get("text")
                        
                        provider_ts = self._parse_timestamp(value.get("timestamp"))

                        norm_msg = NormalizedInboundMessage(
                            channel="INSTAGRAM",
                            external_message_id=message_id,
                            external_user_id=sender_id,
                            sender_name=None,
                            sender_username=None,
                            sender_phone=None,
                            text=text,
                            message_type="TEXT",
                            attachments=[],
                            provider_timestamp=provider_ts,
                            raw_metadata=value,
                        )
                        normalized_messages.append(norm_msg)

        logger.info(
            "Parsed %d normalized Instagram messages from webhook payload.",
            len(normalized_messages),
        )
        return normalized_messages
