import base64
import hashlib
import hmac
import json
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings

class MetaCallbacksTests(APITestCase):

    def setUp(self):
        self.deauthorize_url = reverse("api_v1:integrations:oauth-instagram-deauthorize")
        self.data_deletion_url = reverse("api_v1:integrations:oauth-instagram-data-deletion")
        self.app_secret = getattr(settings, "META_APP_SECRET", "test_secret")

    def _generate_signed_request(self, payload: dict) -> str:
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

    @patch("dotenv.set_key")
    def test_deauthorize_success(self, mock_set_key):
        payload = {"user_id": "12345"}
        signed_request = self._generate_signed_request(payload)
        
        response = self.client.post(self.deauthorize_url, {"signed_request": signed_request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        
        mock_set_key.assert_called_once()
        args, kwargs = mock_set_key.call_args
        self.assertEqual(args[1], "INSTAGRAM_ACCESS_TOKEN")
        self.assertEqual(args[2], "")

    @patch("dotenv.set_key")
    def test_data_deletion_success(self, mock_set_key):
        payload = {"user_id": "12345"}
        signed_request = self._generate_signed_request(payload)
        
        response = self.client.post(self.data_deletion_url, {"signed_request": signed_request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertIn("confirmation_code", response.data)
        self.assertEqual(response.data["confirmation_code"], "12345")
        
        mock_set_key.assert_called_once()
        args, kwargs = mock_set_key.call_args
        self.assertEqual(args[1], "INSTAGRAM_ACCESS_TOKEN")
        self.assertEqual(args[2], "")
