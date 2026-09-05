"""
Unified exception handling and standardized API error formatting.
"""
import logging
from typing import Any, Optional
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler
from apps.core.logging import get_correlation_id

logger = logging.getLogger("apps.exceptions")


# ---------------------------------------------------------------------------
# Domain Exception Classes
# ---------------------------------------------------------------------------

class ApplicationError(Exception):
    """Base exception for application business logic errors."""
    default_message = "An unexpected application error occurred."
    default_code = "application_error"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        errors: Optional[Any] = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.errors = errors
        super().__init__(self.message)


class ConflictError(ApplicationError):
    """Raised when a concurrency or resource conflict occurs (e.g. double booking)."""
    default_message = "Resource conflict occurred. The requested slot or resource is no longer available."
    default_code = "conflict_error"
    status_code = status.HTTP_409_CONFLICT


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""
    default_message = "Requested resource was not found."
    default_code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND


class ExternalServiceError(ApplicationError):
    """
    Raised when a dependent external service (Meta API, WhatsApp, etc.) fails.
    Mapped to HTTP 502 Bad Gateway so clients know the error is upstream.
    Never expose the raw upstream error message to end-users.
    """
    default_message = "An external service is temporarily unavailable. Please try again shortly."
    default_code = "external_service_error"
    status_code = status.HTTP_502_BAD_GATEWAY


class AuthenticationError(ApplicationError):
    """Raised for custom authentication or token validation failures."""
    default_message = "Authentication failed. Please log in again."
    default_code = "authentication_error"
    status_code = status.HTTP_401_UNAUTHORIZED


class RateLimitError(ApplicationError):
    """Raised when a rate limit is exceeded on an external service."""
    default_message = "Rate limit exceeded. Please wait before retrying."
    default_code = "rate_limit_exceeded"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


# ---------------------------------------------------------------------------
# Custom DRF Exception Handler
# ---------------------------------------------------------------------------

def custom_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Custom exception handler that ensures all REST API error responses
    follow a consistent, structured JSON format:

        {
          "status": "error",
          "code": "<machine_readable_code>",
          "message": "<user_facing_message>",
          "errors": { ... },
          "correlation_id": "<uuid>"
        }

    NEVER exposes: Python tracebacks, raw database errors, internal file paths,
    infrastructure details, or secrets.
    """
    correlation_id = get_correlation_id()

    # ------------------------------------------------------------------
    # 1. Custom domain ApplicationErrors (our own exception hierarchy)
    # ------------------------------------------------------------------
    if isinstance(exc, ApplicationError):
        # Log server-side errors with full traceback for diagnostics
        if exc.status_code >= 500:
            logger.exception(
                "ApplicationError [%s] correlation_id=%s: %s",
                exc.code, correlation_id, exc.message,
                exc_info=True,
            )
        else:
            logger.warning(
                "ApplicationError [%s] correlation_id=%s: %s",
                exc.code, correlation_id, exc.message,
            )
        return Response(
            {
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors or {},
                "correlation_id": correlation_id,
            },
            status=exc.status_code,
        )

    # ------------------------------------------------------------------
    # 2. Django core validation errors
    # ------------------------------------------------------------------
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            errors = exc.message_dict
        elif hasattr(exc, "messages"):
            errors = {"detail": exc.messages}
        else:
            errors = {"detail": [str(exc)]}
        return Response(
            {
                "status": "error",
                "code": "validation_error",
                "message": "Validation failed. Please check the provided data.",
                "errors": errors,
                "correlation_id": correlation_id,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ------------------------------------------------------------------
    # 3. Standard DRF exceptions — let DRF build the base response first,
    #    then reformat it into our envelope.
    # ------------------------------------------------------------------
    response = exception_handler(exc, context)

    if response is not None:
        code = "error"
        message = "An error occurred. Please try again."
        errors: Any = {}

        if isinstance(exc, DRFValidationError):
            code = "validation_error"
            message = "Validation failed. Please check the provided data."
            errors = response.data

        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = "authentication_required"
            message = "Authentication is required. Please log in."
            # Never surface DRF authentication internals
            errors = {}

        elif isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
            code = "permission_denied"
            message = "You do not have permission to perform this action."
            errors = {}

        elif isinstance(exc, Throttled):
            code = "rate_limit_exceeded"
            wait = getattr(exc, "wait", None)
            message = (
                f"Too many requests. Please wait {int(wait)} seconds before retrying."
                if wait else "Too many requests. Please try again later."
            )
            errors = {}

        elif isinstance(exc, Http404):
            code = "not_found"
            message = "The requested resource was not found."
            errors = {}

        elif exc.__class__.__name__ == "MessagingUnavailable":
            detail = exc.detail
            code = str(detail.get("code", "configuration_required")) if isinstance(detail, dict) else "configuration_required"
            message = str(detail.get("message", detail)) if isinstance(detail, dict) else str(detail)
            errors = {}

        elif isinstance(exc, APIException) and getattr(exc, "default_code", "") == "payment_unavailable":
            code = "payment_unavailable"
            message = str(exc.detail)

        elif isinstance(exc, APIException):
            code = getattr(exc, "default_code", "api_error") or "api_error"
            message = "An error occurred. Please try again."
            errors = {}

        response.data = {
            "status": "error",
            "code": code,
            "message": message,
            "errors": errors,
            "correlation_id": correlation_id,
        }
        return response

    # ------------------------------------------------------------------
    # 4. Unhandled / unexpected 500 exceptions
    #    Log full traceback server-side, return safe generic message.
    # ------------------------------------------------------------------
    logger.exception(
        "Unhandled exception [correlation_id=%s]: %s",
        correlation_id, str(exc),
        exc_info=True,
    )
    return Response(
        {
            "status": "error",
            "code": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "errors": {},
            "correlation_id": correlation_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


