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

            return existing_event, False

    @classmethod
    @transaction.atomic
    def process_raw_webhook_event(cls, raw_event, plog=None):
        from apps.integrations.models import IntegrationConfig
        from apps.leads.capture import capture_message_lead
        from apps.automations.services import evaluate_message
        raw_event = RawWebhookEvent.objects.select_for_update().get(pk=raw_event.pk)
        if raw_event.status == RawWebhookEvent.Status.PROCESSED:
            return {"success": True, "messages_processed": 0, "is_duplicate": True}
        payload = raw_event.payload
        parser = cls._find_parser_for_payload(payload)
        counts = {"success": True, "messages_processed": 0, "statuses_processed": 0, "new_messages_created": 0, "leads_created": 0}
        if not parser:
            return {**counts, "notes": "Unsupported object type"}

        def resolve(channel, destination, aliases=(), sender_id=None):
            if channel == "INSTAGRAM":
                from apps.integrations.meta.instagram.identity import matching_configs
                query = matching_configs((destination, *aliases))
            else:
                query = IntegrationConfig.objects.filter(provider=channel, metadata__destination_id=destination,
                    is_active=True, organization__is_active=True, organization__is_deleted=False)
            configs = list(query.select_for_update(of=("self",)).select_related("organization"))
            if channel == "INSTAGRAM":
                logger.info("instagram_destination_resolved", extra={"stage": "instagram_destination_resolved",
                    "raw_event_id": str(raw_event.pk), "destination_id": destination,
                    "destination_aliases": aliases, "sender_id": sender_id, "resolution_matches": len(configs)})
            if len(configs) != 1:
                raise ValueError("Webhook destination is unconfigured or assigned to multiple workspaces.")
            config = configs[0]
            config.metadata = {**config.metadata, "last_event_time": raw_event.created_at.isoformat()}
            config.save(update_fields=["metadata", "updated_at"])
            return config.organization

        # Status callbacks are routed by the receiving phone/account, never globally.
        for entry in payload.get("entry", []):
            if isinstance(parser, WhatsAppInboundParser):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if not value.get("statuses"):
                        continue
                    org = resolve("WHATSAPP", str(value.get("metadata", {}).get("phone_number_id", "")))
                    for st in parser.parse_status_updates({"object": payload["object"], "entry": [{"changes": [change]}]}):
                        msg = ConversationService.update_message_delivery_status(st.external_message_id, st.status, st.error_details, st.timestamp, organization=org, channel="WHATSAPP")
                        if msg:
                            counts["statuses_processed"] += 1
                            transaction.on_commit(lambda m=msg: broadcast_message_updated(m))
            else:
                for event in entry.get("messaging", []):
                    read_id = event.get("read", {}).get("mid")
                    delivery_ids = event.get("delivery", {}).get("mids", [])
                    if not read_id and not delivery_ids:
                        continue
                    org = resolve("INSTAGRAM", str(entry.get("id", "")))
                    for mid in ([read_id] if read_id else delivery_ids):
                        msg = ConversationService.update_message_delivery_status(mid, "read" if read_id else "delivered", organization=org, channel="INSTAGRAM")
                        if msg:
                            counts["statuses_processed"] += 1
                            transaction.on_commit(lambda m=msg: broadcast_message_updated(m))

        for normalized in parser.parse_messages(payload):
            if normalized.channel == "INSTAGRAM":
                logger.info("instagram_message_normalized", extra={"stage": "instagram_message_normalized",
                    "raw_event_id": str(raw_event.pk), "destination_id": normalized.destination_id,
                    "sender_id": normalized.external_user_id})
            org = resolve(normalized.channel, normalized.destination_id, normalized.destination_aliases, normalized.external_user_id)
            message, created = ConversationService.store_inbound_message(normalized.to_service_dict(), organization=org, plog=plog)
            counts["messages_processed"] += 1
            if not created:
                continue
            counts["new_messages_created"] += 1
            # Lock the customer before the legacy trigger detector and default capture.
            from apps.customers.models import Customer
            Customer.objects.select_for_update().get(pk=message.conversation.customer_id)
            lead, lead_created, trigger = LeadDetectionService.process_inbound_message(message, plog=plog)
            # Instagram leads require keyword intent; WhatsApp retains its existing capture-all policy.
            if not lead and normalized.channel != "INSTAGRAM":
                lead, lead_created = capture_message_lead(message)
            if lead_created:
                counts["leads_created"] += 1
                transaction.on_commit(lambda l=lead: broadcast_new_lead(l))
            evaluate_message(message, new_lead=lead_created)
            transaction.on_commit(lambda m=message, l=lead: broadcast_new_message(m, lead_id=str(l.pk) if l else None))
        raw_event.status = RawWebhookEvent.Status.PROCESSED
        from django.utils import timezone
        raw_event.processed_at = timezone.now()
        raw_event.error_message = ""
        raw_event.messages_count = counts["messages_processed"] + counts["statuses_processed"]
        raw_event.save(update_fields=["status", "processed_at", "error_message", "messages_count", "updated_at"])
        return counts

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
