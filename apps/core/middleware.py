"""
Custom middleware for request tracking and observability.
"""
import logging
import time
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse
from apps.core.logging import set_correlation_id

logger = logging.getLogger("apps.request")


class CorrelationIdMiddleware:
    """
    Ensures every HTTP request has a unique correlation ID.
    Attaches it to contextvars, request object, and response headers.
    """
    HEADER_NAME = "HTTP_X_CORRELATION_ID"
    FALLBACK_HEADER = "HTTP_X_REQUEST_ID"
    RESPONSE_HEADER = "X-Correlation-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = (
            request.META.get(self.HEADER_NAME)
            or request.META.get(self.FALLBACK_HEADER)
            or str(uuid.uuid4())
        )
        set_correlation_id(correlation_id)
        request.correlation_id = correlation_id

        response = self.get_response(request)
        response[self.RESPONSE_HEADER] = correlation_id
        return response


class StructuredLoggingMiddleware:
    """
    Logs incoming HTTP requests and response timing.
    """
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.perf_counter()
        
        # Don't log spammy internal health checks at INFO level in production
        is_health = request.path in ("/health/", "/api/v1/health/")

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not is_health:
            logger.info(
                f"{request.method} {request.path} {response.status_code} ({duration_ms:.2f}ms)"
            )

        return response
