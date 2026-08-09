"""
Tests for health check and ping endpoints.
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
def test_root_health_check(api_client):
    """Test /health/ready/ endpoint returns 200 OK with expected structure."""
    response = api_client.get("/health/ready/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "checks" in data
    assert "database" in data["checks"]
    assert "cache" in data["checks"]
    assert data["checks"]["database"]["status"] == "healthy"
    assert data["checks"]["cache"]["status"] == "healthy"
    assert "X-Correlation-ID" in response.headers


@pytest.mark.django_db
def test_api_v1_health_check(api_client):
    """Test /api/v1/health/ready/ endpoint returns 200 OK."""
    response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_root_ping(api_client):
    """Test /health/live/ endpoint returns 200 OK."""
    response = api_client.get("/health/live/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
