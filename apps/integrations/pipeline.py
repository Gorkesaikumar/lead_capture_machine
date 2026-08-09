"""
Inbound Pipeline Orchestrator.
Decouples external Meta provider normalization from domain business workflows
(Customer Resolution, Conversation Persistence, Delivery Status Tracking, and Lead Detection).
Supports synchronous and asynchronous processing from RawWebhookEvent records.
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from django.db import IntegrityError, transaction
from apps.conversations.services import ConversationService
from apps.integrations.meta.base import InboundMessageParser, NormalizedInboundMessage
from apps.integrations.meta.common.verifier import MetaSignatureVerifier
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.meta.whatsapp.parser import WhatsAppInboundParser
from apps.integrations.models import RawWebhookEvent
from apps.leads.services import LeadDetectionService
from apps.core.realtime import (
    broadcast_new_message,
    broadcast_message_updated,
    broadcast_new_lead,
    broadcast_lead_updated,
)
from apps.core.logging import PipelineLogger, PipelineStage

logger = logging.getLogger("apps.integrations.pipeline")


class InboundPipelineService:
    """
    Orchestrates ingestion, deduplication, and domain handoff for incoming Meta webhooks
    (Instagram and WhatsApp Cloud API).
    """

    _PARSERS: List[InboundMessageParser] = [
        InstagramInboundParser(),
        WhatsAppInboundParser(),
    ]

    @classmethod
    def generate_event_id(cls, payload: Dict[str, Any], channel: str = "INSTAGRAM") -> str:
        """
        Generates a deterministic unique identifier for the webhook payload.
        Prioritizes message ID or status ID; falls back to SHA-256 hash of payload.
        """
        try:
            entries = payload.get("entry", [])
            if entries and isinstance(entries, list):
                first_entry = entries[0]
                # Instagram single message
                if channel == "INSTAGRAM":
                    messaging = first_entry.get("messaging", [])
                    if messaging and isinstance(messaging, list):
                        first_msg = messaging[0].get("message", {})
                        mid = first_msg.get("mid")
                        if mid:
                            return f"ig_mid_{mid}"

                    changes = first_entry.get("changes", [])
                    if changes and isinstance(changes, list):
                        val = changes[0].get("value", {})
                        if isinstance(val, dict):
                            msg_obj = val.get("message", {})
                            mid = msg_obj.get("mid")
                            if mid:
                                return f"ig_changes_mid_{mid}"

                # WhatsApp message or status
                elif channel == "WHATSAPP":
                    changes = first_entry.get("changes", [])
                    if changes and isinstance(changes, list):
                        val = changes[0].get("value", {})
                        messages = val.get("messages", [])
                        if messages and len(messages) == 1:
                            wamid = messages[0].get("id")
                            if wamid:
                                return f"wa_mid_{wamid}"
                        statuses = val.get("statuses", [])
                        if statuses and len(statuses) == 1:
                            st = statuses[0]
                            st_id = st.get("id")
                            st_name = st.get("status")
                            if st_id and st_name:
                                return f"wa_status_{st_id}_{st_name}"
        except Exception as e:
            logger.warning("generate_event_id parsing error: %s", e)

        # Fallback to deterministic SHA-256 of normalized JSON payload
        serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        hash_id = hashlib.sha256(serialized).hexdigest()
        return f"hash_{hash_id}"

    @classmethod
    def record_raw_event(
        cls,
        channel: str,
        raw_body: bytes,
        signature_header: Optional[str],
        payload: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        plog: Optional[PipelineLogger] = None,
    ) -> Tuple[RawWebhookEvent, bool]:
        """
        Idempotently records a RawWebhookEvent in the database.

        Returns:
            Tuple[RawWebhookEvent, bool]: (event instance, is_new boolean)
        """
        event_id = cls.generate_event_id(payload, channel=channel)
        sig = signature_header or ""

        if plog:
            plog.set(event_id=event_id)

        try:
            with transaction.atomic():
                event = RawWebhookEvent.objects.create(
                    channel=channel,
                    event_id=event_id,
                    signature=sig,
                    headers=headers or {},
                    payload=payload,
                    status=RawWebhookEvent.Status.PENDING,
                )
                if plog:
                    plog.info(
                        PipelineStage.RAW_EVENT_SAVED,
                        "New RawWebhookEvent created",
                        raw_event_db_id=str(event.id),
                        is_duplicate=False,
                    )
                else:
                    logger.info(
                        "New RawWebhookEvent created",
                        extra={
                            "stage": PipelineStage.RAW_EVENT_SAVED,
                            "event_id": event_id,
                            "raw_event_db_id": str(event.id),
                            "channel": channel,
                            "is_duplicate": False,
                        },
                    )
                return event, True
        except IntegrityError:
            # Duplicate event already recorded
            existing_event = RawWebhookEvent.objects.filter(
                channel=channel, event_id=event_id
            ).first()

            if plog:
                plog.info(
                    PipelineStage.RAW_EVENT_SAVED,
                    "Duplicate RawWebhookEvent detected — skipping",
                    raw_event_db_id=str(existing_event.id) if existing_event else None,
                    existing_status=str(existing_event.status) if existing_event else None,
                    is_duplicate=True,
                )
            else:
                logger.info(
                    "Duplicate RawWebhookEvent detected",
                    extra={
                        "stage": PipelineStage.RAW_EVENT_SAVED,
                        "event_id": event_id,
                        "is_duplicate": True,
                        "existing_status": str(existing_event.status) if existing_event else None,
                    },
                )

            if existing_event and existing_event.status == RawWebhookEvent.Status.PENDING:
                existing_event.status = RawWebhookEvent.Status.DUPLICATE
                existing_event.save(update_fields=["status", "updated_at"])

            return existing_event, False

    @classmethod
    def process_raw_webhook_event(
        cls,
        raw_event: RawWebhookEvent,
        plog: Optional[PipelineLogger] = None,
    ) -> Dict[str, Any]:
        """
        Processes an existing RawWebhookEvent record through parser, conversation, status update,
        and lead services.
        """
        # Create or reuse a PipelineLogger scoped to this event
        if plog is None:
            plog = PipelineLogger(
                base_logger=logger,
                event_id=raw_event.event_id,
                channel=raw_event.channel,
            )
        else:
            plog.set(event_id=raw_event.event_id, channel=raw_event.channel)

        payload = raw_event.payload
        plog.debug(PipelineStage.PAYLOAD_PARSED, "Selecting parser for payload object type",
                   object_type=payload.get("object"))

        parser = cls._find_parser_for_payload(payload)
        if not parser:
            plog.warning(
                PipelineStage.PAYLOAD_PARSED,
                "No parser found for payload — unsupported object type",
                object_type=payload.get("object"),
            )
            return {
                "success": True,
                "messages_processed": 0,
                "statuses_processed": 0,
                "notes": "Unsupported object type",
            }

        plog.debug(PipelineStage.PAYLOAD_PARSED, "Parser selected",
                   parser=type(parser).__name__)

        # 1. Process WhatsApp Status Updates (if present)
        statuses_processed_count = 0
        if isinstance(parser, WhatsAppInboundParser):
            status_updates = parser.parse_status_updates(payload)
            for st in status_updates:
                updated_msg = ConversationService.update_message_delivery_status(
                    external_message_id=st.external_message_id,
                    delivery_status=st.status,
                    error_details=st.error_details,
                    provider_timestamp=st.timestamp,
                )
                if updated_msg:
                    statuses_processed_count += 1
                    plog.info(
                        PipelineStage.MESSAGE_SAVED,
                        "WhatsApp delivery status updated",
                        external_message_id=st.external_message_id,
                        delivery_status=st.status,
                    )
                    broadcast_message_updated(updated_msg)

        # 2. Process Inbound Messages
        normalized_messages = parser.parse_messages(payload)
        processed_count = 0
        created_messages_count = 0
        leads_created_count = 0

        for norm_msg in normalized_messages:
            plog.debug(
                PipelineStage.PAYLOAD_PARSED,
                "Processing normalized inbound message",
                external_message_id=norm_msg.external_message_id,
                channel=norm_msg.channel,
                message_type=getattr(norm_msg, "message_type", None),
            )

            msg_instance, was_created = ConversationService.store_inbound_message(
                norm_msg.to_service_dict(),
                plog=plog,
            )
            processed_count += 1

            if was_created:
                created_messages_count += 1

                # Trigger Lead Detection on newly created message
                plog.info(
                    PipelineStage.LEAD_DETECTION,
                    "Running lead detection",
                    message_id=str(msg_instance.id),
                    external_message_id=str(msg_instance.external_message_id or ""),
                )
                lead, lead_created, matched_trigger = LeadDetectionService.process_inbound_message(
                    msg_instance,
                    plog=plog,
                )

                if lead and lead_created:
                    leads_created_count += 1
                    plog.info(
                        PipelineStage.LEAD_CREATED,
                        "New lead created",
                        lead_id=str(lead.id),
                        customer_id=str(lead.customer_id),
                        trigger_id=str(matched_trigger.id) if matched_trigger else None,
                    )
                    broadcast_new_lead(lead)
                elif lead:
                    broadcast_lead_updated(lead)

                # Broadcast new message to dashboard
                plog.info(
                    PipelineStage.WEBSOCKET_BROADCAST,
                    "Broadcasting new message event",
                    message_id=str(msg_instance.id),
                    lead_id=str(lead.id) if lead else None,
                    conversation_id=str(msg_instance.conversation_id),
                )
                broadcast_new_message(msg_instance, lead_id=str(lead.id) if lead else None)

        plog.info(
            PipelineStage.RAW_EVENT_SAVED,
            "Webhook event processing complete",
            new_messages=created_messages_count,
            total_processed=processed_count,
            statuses_processed=statuses_processed_count,
            leads_created=leads_created_count,
        )
        return {
            "success": True,
            "messages_processed": processed_count,
            "statuses_processed": statuses_processed_count,
            "new_messages_created": created_messages_count,
            "leads_created": leads_created_count,
        }

    @classmethod
    def process_webhook_payload(
        cls,
        raw_body: bytes,
        signature_header: Optional[str],
        payload: Dict[str, Any],
        verify_signature: bool = True,
        channel: str = "INSTAGRAM",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous end-to-end webhook processing (verifies, records raw event, parses, and persists).
        Used during synchronous test suites and immediate pipeline executions.
        """
        plog = PipelineLogger(
            base_logger=logger,
            channel=channel,
            request_id=request_id,
        )

        plog.info(
            PipelineStage.WEBHOOK_RECEIVED,
            "Webhook payload received for processing",
            channel=channel,
            verify_signature=verify_signature,
        )

        if verify_signature:
            MetaSignatureVerifier.verify_signature(raw_body, signature_header)
            plog.info(PipelineStage.SIGNATURE_VERIFIED, "HMAC signature verified")

        raw_event, is_new = cls.record_raw_event(
            channel=channel,
            raw_body=raw_body,
            signature_header=signature_header,
            payload=payload,
            plog=plog,
        )

        if not is_new and raw_event.status in [RawWebhookEvent.Status.PROCESSED, RawWebhookEvent.Status.DUPLICATE]:
            plog.info(
                PipelineStage.RAW_EVENT_SAVED,
                "Duplicate event skipped — already processed",
                event_id=raw_event.event_id,
            )
            return {
                "success": True,
                "event_id": str(raw_event.id),
                "messages_processed": 0,
                "statuses_processed": 0,
                "new_messages_created": 0,
                "leads_created": 0,
                "is_duplicate": True,
            }

        result = cls.process_raw_webhook_event(raw_event, plog=plog)

        raw_event.status = RawWebhookEvent.Status.PROCESSED
        raw_event.messages_count = result.get("messages_processed", 0) + result.get("statuses_processed", 0)
        raw_event.save(update_fields=["status", "messages_count", "updated_at"])

        result["event_id"] = str(raw_event.id)
        result["is_duplicate"] = False
        return result

    @classmethod
    def _find_parser_for_payload(cls, payload: Dict[str, Any]) -> Optional[InboundMessageParser]:
        """
        Iterates registered parsers to identify one that can parse the payload.
        """
        for parser in cls._PARSERS:
            if parser.can_parse(payload):
                return parser
        return None
