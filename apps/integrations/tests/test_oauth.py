from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache
from django.test import override_settings
from apps.integrations.connection_service import create_attempt, SCOPES
from apps.integrations.models import OAuthAttempt
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization
from apps.integrations.models import IntegrationConfig

User = get_user_model()


@override_settings(META_REDIRECT_BASE_URL="https://api.example.test", META_INSTAGRAM_REDIRECT_URI="", FRONTEND_URL="https://app.example.test", META_INSTAGRAM_APP_ID="", META_INSTAGRAM_APP_SECRET="")
class InstagramOAuthTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="admin@example.com", password="password", is_staff=True)
        self.org = make_organization(name="Test Org", slug="test-org")
        add_member(self.user, self.org)
        self.user.organization = self.org
        self.user.save()

        self.login_url = reverse("api_v1:integrations:oauth-instagram-login")
        self.callback_url = reverse("api_v1:integrations:oauth-instagram-callback")

    def test_oauth_login_start_requires_auth(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_oauth_login_start_returns_url(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertIn("https://www.instagram.com/oauth/authorize", response.data["url"])
        self.assertIn("state=", response.data["url"])

    def test_oauth_callback_missing_parameters(self):
        response = self.client.get(self.callback_url)
        # It's a redirect to the frontend with an error
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    def test_oauth_callback_invalid_state(self):
        response = self.client.get(f"{self.callback_url}?code=123&state=invalid")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    def test_oauth_callback_denied_authorization(self):
        response = self.client.get(f"{self.callback_url}?error=access_denied&error_description=user_denied")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    @patch("requests.post")
    @patch("requests.get")
    def test_oauth_callback_success(self, mock_get, mock_post):
        # Setup mock state mapped to org ID
        state = create_attempt(self.user, self.org, "INSTAGRAM", "https://api.example.test/api/v1/integrations/oauth/instagram/callback/")

        # Mock requests.post to return a successful token response
        class MockPostResponse:
            status_code = 200
            def json(self):
                return {"access_token": "mocked_short_token", "user_id": 12345, "success": True}

        class MockGetResponse:
            status_code = 200
            def json(self):
                return {"access_token": "mocked_long_lived_token", "expires_in": 5184000, "user_id": "12345", "username": "testuser", "data": [{"permission": p, "status": "granted"} for p in SCOPES["INSTAGRAM"]]}

        mock_post.return_value = MockPostResponse()
        mock_get.return_value = MockGetResponse()

        response = self.client.get(f"{self.callback_url}?code=validcode&state={state}")
        
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("integration_success=instagram", response.url)
        
        # Verify IntegrationConfig was created for self.org
        config = IntegrationConfig.objects.filter(organization=self.org, provider="INSTAGRAM").first()
        self.assertIsNotNone(config)
        self.assertTrue(config.is_active)
        self.assertEqual(config.metadata.get("account_id"), "12345")

        # Verify state is cleared
        self.assertIsNotNone(OAuthAttempt.objects.get().consumed_at)
