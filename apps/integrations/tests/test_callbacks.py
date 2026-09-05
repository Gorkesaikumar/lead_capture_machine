from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
import base64
import hashlib
import hmac
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings
from apps.organizations.models import Organization
from apps.integrations.models import IntegrationConfig

class MetaCallbacksTests(APITestCase):

    def setUp(self):
        self.deauthorize_url = reverse("api_v1:integrations:oauth-instagram-deauthorize")
        self.data_deletion_url = reverse("api_v1:integrations:oauth-instagram-data-deletion")
        self.app_secret = getattr(settings, "META_APP_SECRET", "test_secret")

        self.org = make_organization(name="Test Org", slug="test-org")
        self.config = IntegrationConfig.objects.create(
            organization=self.org,
            provider="INSTAGRAM",
            is_active=True,
            metadata={"account_id": "12345"}
        )

    def _generate_signed_request(self, payload: dict) -> str:
        payload["algorithm"] = "HMAC-SHA256"
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip("=")
        sig = hmac.new(
            self.app_secret.encode('utf-8'),
            encoded_payload.encode('utf-8'),
            hashlib.sha256
        ).digest()
        encoded_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip("=")
        return f"{encoded_sig}.{encoded_payload}"

    def test_deauthorize_missing_signed_request(self):
        response = self.client.post(self.deauthorize_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Missing signed_request")

    def test_deauthorize_invalid_signature(self):
        response = self.client.post(self.deauthorize_url, {"signed_request": "invalid.signature"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid signature")

    def test_deauthorize_success(self):
        payload = {"user_id": "12345"}
        signed_request = self._generate_signed_request(payload)
        
        response = self.client.post(self.deauthorize_url, {"signed_request": signed_request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        
        # Keep only account mapping so a subsequent signed deletion can identify its workspace.
        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)
        self.assertEqual(self.config.credentials, {})

    def test_data_deletion_success(self):
        payload = {"user_id": "12345"}
        signed_request = self._generate_signed_request(payload)
        
        response = self.client.post(self.data_deletion_url, {"signed_request": signed_request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertIn("confirmation_code", response.data)
        self.assertNotEqual(response.data["confirmation_code"], "12345")
        status_response = self.client.get(response.data["url"])
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "PENDING")
        
        # Verify IntegrationConfig was deleted
        self.assertFalse(IntegrationConfig.objects.filter(id=self.config.id).exists())
