"""
Core system views including health check and readiness endpoints.
"""
import time
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.logging import get_correlation_id
import logging

logger = logging.getLogger("apps.core.views")


class HealthReadyView(APIView):
    """
    Health check endpoint verifying database and cache connectivity.
    Returns HTTP 200 when all services are healthy, HTTP 503 otherwise.
    Internal error details are logged server-side, never returned to clients.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        health_data = {
            "status": "healthy",
            "service": settings.STUDIO_NAME,
            "version": "1.0.0",
            "correlation_id": get_correlation_id(),
            "checks": {},
        }
        all_healthy = True

        # Database Check
        db_start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            db_duration_ms = (time.perf_counter() - db_start) * 1000
            health_data["checks"]["database"] = {
                "status": "healthy",
                "latency_ms": round(db_duration_ms, 2),
            }
        except Exception as e:
            all_healthy = False
            # Log internally with full details but never expose to clients
            logger.error("Health check: database unavailable: %s", str(e), exc_info=True)
            health_data["checks"]["database"] = {
                "status": "unhealthy",
                "error": "Database connection failed.",
            }

        # Cache Check
        cache_start = time.perf_counter()
        try:
            test_key = "__healthcheck_probe__"
            cache.set(test_key, "ok", 10)
            val = cache.get(test_key)
            if val != "ok":
                raise ValueError("Cache read/write mismatch")
            cache_duration_ms = (time.perf_counter() - cache_start) * 1000
            health_data["checks"]["cache"] = {
                "status": "healthy",
                "latency_ms": round(cache_duration_ms, 2),
            }
        except Exception as e:
            all_healthy = False
            logger.error("Health check: cache unavailable: %s", str(e), exc_info=True)
            health_data["checks"]["cache"] = {
                "status": "unhealthy",
                "error": "Cache connection failed.",
            }

        if not all_healthy:
            health_data["status"] = "unhealthy"
            return Response(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_data, status=status.HTTP_200_OK)


class HealthLiveView(APIView):
    """Simple lightweight ping view for liveness probes."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        return Response({"status": "alive", "timestamp": time.time()})

