"""
Tests for custom exception handler and error response structure.
"""
import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError, NotFound
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from apps.core.exceptions import (
    ApplicationError,
    ConflictError,
    ResourceNotFoundError,
    custom_exception_handler,
)


def test_conflict_error_handling():
    """Verify ConflictError maps to HTTP 409 and structured format."""
    factory = APIRequestFactory()
    request = factory.get("/")
    drf_request = Request(request)
    context = {"request": drf_request}

    exc = ConflictError(message="Slot already reserved", code="slot_conflict")
    response = custom_exception_handler(exc, context)

    assert response is not None
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.data
    assert data["status"] == "error"
    assert data["code"] == "slot_conflict"
    assert data["message"] == "Slot already reserved"
    assert "correlation_id" in data


def test_drf_not_found_handling():
    """Verify standard DRF NotFound maps cleanly to standardized format."""
    factory = APIRequestFactory()
    request = factory.get("/")
    drf_request = Request(request)
    context = {"request": drf_request}

    exc = NotFound(detail="Service not found.")
    response = custom_exception_handler(exc, context)

    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.data
    assert data["status"] == "error"
    assert data["code"] == "not_found"
    assert "correlation_id" in data
