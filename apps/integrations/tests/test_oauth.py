from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model


User = get_user_model()


class InstagramOAuthTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="admin@example.com", password="password", is_staff=True)
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
        self.assertIn("https://api.instagram.com/oauth/authorize", response.data["url"])
        self.assertIn("state=", response.data["url"])

    def test_oauth_callback_missing_parameters(self):
        response = self.client.get(self.callback_url)
        # It's a redirect to the frontend with an error
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=missing_parameters", response.url)

    def test_oauth_callback_invalid_state(self):
        response = self.client.get(f"{self.callback_url}?code=123&state=invalid")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    def test_oauth_callback_denied_authorization(self):
        response = self.client.get(f"{self.callback_url}?error=access_denied&error_description=user_denied")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=access_denied", response.url)

    @patch("requests.post")
    @patch("dotenv.set_key")
    def test_oauth_callback_success(self, mock_set_key, mock_post):
        # Setup mock state
        cache.set("oauth_state_validstate123", True, 60)

        # Mock requests.post to return a successful token response
        class MockResponse:
            status_code = 200
            def json(self):
                return {"access_token": "mocked_long_lived_token", "user_id": 12345}

        mock_post.return_value = MockResponse()

        response = self.client.get(f"{self.callback_url}?code=validcode&state=validstate123")
        
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("integration_success=instagram", response.url)
        
        # Verify dotenv was called to save the token and account ID
        self.assertEqual(mock_set_key.call_count, 2)
        call_args_list = mock_set_key.call_args_list
        self.assertEqual(call_args_list[0][0][1], "INSTAGRAM_ACCESS_TOKEN")
        self.assertEqual(call_args_list[0][0][2], "mocked_long_lived_token")
        self.assertEqual(call_args_list[1][0][1], "INSTAGRAM_ACCOUNT_ID")
        self.assertEqual(call_args_list[1][0][2], "12345")

        # Verify state is cleared
        self.assertIsNone(cache.get("oauth_state_validstate123"))
