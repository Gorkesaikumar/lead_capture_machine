"""
Structured logging utilities for production-grade observability.

Provides:
- JSON-formatted log output (one JSON object per line) for Docker / log aggregators
- Automatic correlation ID injection into every log record
- PipelineLogger context helper for Instagram/WhatsApp stage-by-stage tracing
- Centralized sensitive-field masking so secrets never appear in logs
- Plain-text fallback formatter for local development readability

Design principles:
- Every log line MUST be machine-parseable JSON in production.
- Correlation identifiers are attached to the record at the formatter level.
- Sensitive fields (tokens, secrets, passwords) are masked before output.
- Internal file paths, stack traces, and DB error details stay in the log
  backend only — they are NEVER forwarded to API responses.
"""
import contextvars
import json
import logging
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Correlation ID context variable (request-scoped)
# ---------------------------------------------------------------------------

_correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def get_correlation_id() -> str:
    """Retrieve the current request-scoped correlation ID."""
    return _correlation_id_ctx.get("-")


def set_correlation_id(correlation_id: str) -> None:
    """Bind correlation ID into the current async/thread context."""
    _correlation_id_ctx.set(correlation_id)


# ---------------------------------------------------------------------------
# Sensitive-field masking
# ---------------------------------------------------------------------------

# Keys whose VALUES must never appear in log output (case-insensitive)
SENSITIVE_KEYS = frozenset({
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "app_secret",
    "meta_app_secret",
    "authorization",
    "api_key",
    "signing_secret",
    "webhook_secret",
    "client_secret",
    "code",
    "state",
    "registration_pin",
})

_MASK = "***REDACTED***"


def mask_sensitive(data: Any, _depth: int = 0) -> Any:
    """
    Recursively traverse a dict/list and replace values whose keys match
    SENSITIVE_KEYS with the redaction placeholder.

    Depth is capped at 8 to prevent pathological recursion on huge payloads.
    """
    if _depth > 8:
        return data
    if isinstance(data, dict):
        return {
            k: _MASK if k.lower() in SENSITIVE_KEYS else mask_sensitive(v, _depth + 1)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(item, _depth + 1) for item in data]
    return data


# ---------------------------------------------------------------------------
# Logging filters
# ---------------------------------------------------------------------------

class CorrelationIdFilter(logging.Filter):
    """
    Injects the current request correlation ID into every log record.
    Required by the formatters below — attach to every handler.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        # Development HTTP request lines and HTTP library errors may contain OAuth queries.
        record.msg = re.sub(r"(?i)([?&](?:code|state|access_token|input_token|client_secret|hub\.verify_token)=)[^&\s\"']+", r"\1[REDACTED]", record.getMessage())
        record.args = ()
        return True


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """
    Emits each log record as a single-line JSON object.

    Output is suitable for:
    - Docker log drivers (json-file, fluentd, awslogs)
    - Elasticsearch / OpenSearch ingest
    - Datadog / Papertrail / Grafana Loki
    - Any log aggregator that parses JSON lines

    Standard fields always present:
        timestamp   ISO-8601 UTC
        level       DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger      dotted logger name
        message     the formatted log message
        correlation_id  request-scoped UUID or "-"

    Optional fields added when present:
        stage           pipeline processing stage (see PipelineLogger)
        event_id        webhook event UUID
        external_message_id  provider message ID
        conversation_id
        customer_id
        lead_id
        booking_id
        task_id         Celery task UUID
        exc_type / exc_message / exc_traceback  (on exceptions)
        extra           any remaining extra fields on the record
    """

    # Fields already covered explicitly — skip in generic "extra" dump
    _KNOWN_FIELDS = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "correlation_id",
        # pipeline context fields
        "stage", "event_id", "external_message_id", "conversation_id",
        "customer_id", "lead_id", "booking_id", "task_id", "request_id",
    })

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        correlation_id = getattr(record, "correlation_id", get_correlation_id())

        doc: Dict[str, Any] = {
            "timestamp": now,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id,
        }

        # Pipeline stage identifiers
        for field in (
            "stage", "event_id", "external_message_id", "conversation_id",
            "customer_id", "lead_id", "booking_id", "task_id", "request_id",
        ):
            value = getattr(record, field, None)
            if value is not None:
                doc[field] = str(value)

        # Exception information
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            doc["exc_type"] = exc_type.__name__ if exc_type else None
            doc["exc_message"] = str(exc_value) if exc_value else None
            doc["exc_traceback"] = self.formatException(record.exc_info)

        # Remaining extra fields the caller attached
        extra: Dict[str, Any] = {}
        for key, val in record.__dict__.items():
            if key not in self._KNOWN_FIELDS and not key.startswith("_"):
                extra[key] = val
        if extra:
            doc["extra"] = extra

        try:
            return json.dumps(doc, default=str, ensure_ascii=False)
        except Exception:
            # Fallback: never crash the logging subsystem
            return json.dumps({"timestamp": now, "level": record.levelname, "message": str(record.getMessage())})


class PlainTextFormatter(logging.Formatter):
    """
    Human-readable formatter for local development.
    Includes correlation ID and optional pipeline stage in the prefix.
    """

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        correlation_id = getattr(record, "correlation_id", get_correlation_id())
        stage = getattr(record, "stage", None)
        stage_str = f" [{stage}]" if stage else ""

        prefix = f"{now} [{record.levelname}] [{correlation_id}]{stage_str} {record.name}: "
        message = record.getMessage()

        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return prefix + message


# ---------------------------------------------------------------------------
# Pipeline stage logger helper
# ---------------------------------------------------------------------------

# Canonical stage names for the Instagram/WhatsApp inbound pipeline
class PipelineStage:
    WEBHOOK_RECEIVED     = "webhook_received"
    SIGNATURE_VERIFIED   = "signature_verified"
    PAYLOAD_PARSED       = "payload_parsed"
    RAW_EVENT_SAVED      = "raw_event_saved"
    CUSTOMER_RESOLVED    = "customer_resolved"
    CONVERSATION_RESOLVED = "conversation_resolved"
    MESSAGE_SAVED        = "message_saved"
    LEAD_DETECTION       = "lead_detection"
    LEAD_CREATED         = "lead_created"
    WEBSOCKET_BROADCAST  = "websocket_broadcast"
    # Task lifecycle
    TASK_START           = "task_start"
    TASK_SUCCESS         = "task_success"
    TASK_RETRY           = "task_retry"
    TASK_FAILURE         = "task_failure"
    # Outbound
    OUTBOUND_SEND        = "outbound_send"
    OUTBOUND_SUCCESS     = "outbound_success"
    OUTBOUND_FAILURE     = "outbound_failure"


class PipelineLogger:
    """
    Context-aware structured logger for the Instagram/WhatsApp inbound pipeline.

    Bundles a set of correlation identifiers and attaches them as ``extra``
    fields to every log call so that log aggregators can group, filter, and
    trace a single webhook event end-to-end across all processing stages.

    Usage::

        log = PipelineLogger(
            base_logger=logger,
            event_id="ig_mid_xxx",
            channel="INSTAGRAM",
        )
        log.info(PipelineStage.WEBHOOK_RECEIVED, "Webhook received from Meta")
        log.set(conversation_id="uuid-...", customer_id="uuid-...")
        log.info(PipelineStage.CUSTOMER_RESOLVED, "Customer resolved", created=True)

    All log methods accept arbitrary ``**kwargs`` which are merged into the
    structured ``extra`` payload.
    """

    def __init__(
        self,
        base_logger: logging.Logger,
        *,
        request_id: Optional[str] = None,
        event_id: Optional[str] = None,
        channel: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self._logger = base_logger
        self._ctx: Dict[str, Any] = {}
        if request_id:
            self._ctx["request_id"] = request_id
        if event_id:
            self._ctx["event_id"] = event_id
        if channel:
            self._ctx["channel"] = channel
        if task_id:
            self._ctx["task_id"] = task_id

    def set(self, **kwargs: Any) -> "PipelineLogger":
        """Update the running context with new correlation identifiers."""
        # Strip sensitive values before storing
        for key, value in kwargs.items():
            if key.lower() not in SENSITIVE_KEYS:
                self._ctx[key] = value
        return self

    def _extra(self, stage: str, **kwargs: Any) -> Dict[str, Any]:
        extra = {**self._ctx, "stage": stage}
        # Merge caller kwargs, masking sensitive keys
        for key, value in kwargs.items():
            if key.lower() not in SENSITIVE_KEYS:
                extra[key] = value
        return extra

    def debug(self, stage: str, message: str, **kwargs: Any) -> None:
        self._logger.debug(message, extra=self._extra(stage, **kwargs))

    def info(self, stage: str, message: str, **kwargs: Any) -> None:
        self._logger.info(message, extra=self._extra(stage, **kwargs))

    def warning(self, stage: str, message: str, **kwargs: Any) -> None:
        self._logger.warning(message, extra=self._extra(stage, **kwargs))

    def error(self, stage: str, message: str, **kwargs: Any) -> None:
        self._logger.error(message, extra=self._extra(stage, **kwargs))

    def critical(self, stage: str, message: str, **kwargs: Any) -> None:
        self._logger.critical(message, extra=self._extra(stage, **kwargs))

    def exception(self, stage: str, message: str, **kwargs: Any) -> None:
        """Log an ERROR with full exc_info traceback."""
        self._logger.exception(message, extra=self._extra(stage, **kwargs))
