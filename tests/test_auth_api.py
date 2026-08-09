"""
Comprehensive integration tests for Authentication API endpoints.
"""
import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.authtoken.models import Token
from apps.accounts.models import User

LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to reset rate limiting throttles."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestAuthenticationAPI:
    def test_successful_login(self, api_client, admin_user):
        """6. Successful login returns token and safe user information."""
        response = api_client.post(
            LOGIN_URL,
            data={"email": "admin@v4studio.test", "password": "TestAdminPassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "token" in data["data"]
        assert len(data["data"]["token"]) > 0

        user_data = data["data"]["user"]
        assert user_data["email"] == "admin@v4studio.test"
        assert user_data["full_name"] == "Lead Studio Administrator"
        assert user_data["id"] == str(admin_user.id)
        assert user_data["last_login"] is not None

        # Verify token exists in database
        token_key = data["data"]["token"]
        assert Token.objects.filter(key=token_key, user=admin_user).exists()

    def test_login_invalid_password(self, api_client, admin_user):
        """7. Login rejection with wrong password."""
        response = api_client.post(
            LOGIN_URL,
            data={"email": "admin@v4studio.test", "password": "IncorrectPassword123"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        # New structured error envelope: code = authentication_required
        assert data["status"] == "error"
        assert data["code"] in ("authentication_required", "authentication_error")

    def test_login_unknown_email(self, api_client):
        """8. Login rejection with non-existent email returns generic message."""
        response = api_client.post(
            LOGIN_URL,
            data={"email": "nonexistent@v4studio.test", "password": "SomePassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] in ("authentication_required", "authentication_error")

    def test_login_inactive_user_rejected(self, api_client):
        """9. Inactive admin login is rejected."""
        User.objects.create_user(
            email="inactive_admin@v4studio.test",
            password="SecurePassword123!",
            is_active=False,
        )
        response = api_client.post(
            LOGIN_URL,
            data={"email": "inactive_admin@v4studio.test", "password": "SecurePassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["status"] == "error"

    def test_authenticated_me_endpoint(self, authenticated_client, admin_user):
        """10. Authenticated /me endpoint returns user details."""
        response = authenticated_client.get(ME_URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(admin_user.id)
        assert data["email"] == admin_user.email
        assert data["full_name"] == admin_user.full_name
        assert "created_at" in data

    def test_unauthenticated_me_rejected(self, api_client):
        """11. Unauthenticated request to /me is rejected with 401."""
        response = api_client.get(ME_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalidates_token(self, api_client, admin_user):
        """12. Logout revokes token; subsequent requests with same token fail."""
        # 1. Login to get token
        login_resp = api_client.post(
            LOGIN_URL,
            data={"email": admin_user.email, "password": "TestAdminPassword123!"},
            format="json",
        )
        token_key = login_resp.json()["data"]["token"]

        # 2. Authenticate with token and verify access
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        me_resp = api_client.get(ME_URL)
        assert me_resp.status_code == status.HTTP_200_OK

        # 3. Call logout
        logout_resp = api_client.post(LOGOUT_URL)
        assert logout_resp.status_code == status.HTTP_200_OK
        assert logout_resp.json()["status"] == "success"

        # 4. Verify token was deleted from database
        assert not Token.objects.filter(key=token_key).exists()

        # 5. Subsequent request with revoked token must fail with 401
        post_logout_me = api_client.get(ME_URL)
        assert post_logout_me.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_apis_require_authentication(self, api_client):
        """13. Internal domain APIs reject unauthenticated requests by default."""
        protected_endpoints = [
            "/api/v1/customers/",
            "/api/v1/leads/",
            "/api/v1/conversations/",
            "/api/v1/bookings/",
            "/api/v1/services/",
            "/api/v1/scheduling/",
            "/api/v1/analytics/",
            "/api/v1/integrations/",
        ]
        for endpoint in protected_endpoints:
            response = api_client.get(endpoint)
            # Default permissions reject without auth (either 401 or 404 depending on view existence)
            # Must not be 200 OK without auth
            assert response.status_code in (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            )

    def test_no_public_registration_endpoint(self, api_client):
        """14. Verify there is no public registration endpoint."""
        assert api_client.post("/register/").status_code == status.HTTP_404_NOT_FOUND
        assert api_client.post("/api/v1/auth/register/").status_code == status.HTTP_404_NOT_FOUND
        assert api_client.post("/api/v1/accounts/register/").status_code == status.HTTP_404_NOT_FOUND

    def test_sensitive_fields_never_returned(self, api_client, admin_user, authenticated_client):
        """15. Password, hashes, and internal permissions are never serialized."""
        login_resp = api_client.post(
            LOGIN_URL,
            data={"email": admin_user.email, "password": "TestAdminPassword123!"},
            format="json",
        )
        login_text = login_resp.content.decode("utf-8")
        assert "password" not in login_text.lower() or "TestAdminPassword123!" not in login_text
        assert "pbkdf2" not in login_text
        assert "argon2" not in login_text
        assert "is_superuser" not in login_resp.json()["data"]["user"]
        assert "groups" not in login_resp.json()["data"]["user"]

        me_resp = authenticated_client.get(ME_URL)
        me_text = me_resp.content.decode("utf-8")
        assert "password" not in me_text.lower()
        assert "pbkdf2" not in me_text
        assert "is_superuser" not in me_resp.json()

    def test_login_rate_throttling(self, api_client):
        """16. Exceeding login rate limit triggers 429 Too Many Requests."""
        # Configured rate is 5/minute for auth_login scope
        for _ in range(5):
            api_client.post(
                LOGIN_URL,
                data={"email": "probe@v4studio.test", "password": "WrongPassword123!"},
                format="json",
            )

        # 6th request should trigger rate limit (HTTP 429)
        throttled_response = api_client.post(
            LOGIN_URL,
            data={"email": "probe@v4studio.test", "password": "WrongPassword123!"},
            format="json",
        )
        assert throttled_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
