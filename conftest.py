"""
Pytest configuration and global test fixtures.
"""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from apps.accounts.models import User


@pytest.fixture(autouse=True)
def isolate_cache_between_tests():
    # Django database rollback does not reset Redis/locmem throttle and OAuth state.
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """Returns an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Creates and returns an active Studio Admin user."""
    user = User.objects.create_superuser(
        email="admin@v4studio.test",
        full_name="Lead Studio Administrator",
        password="TestAdminPassword123!",
    )

    from tests.tenant_fixtures import add_member
    add_member(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Creates and returns a DRF auth token for the admin user."""
    token, _ = Token.objects.get_or_create(user=admin_user)
    return token


@pytest.fixture
def authenticated_client(api_client, admin_token):
    """Returns an APIClient authenticated with Token header."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {admin_token.key}")
    return api_client
