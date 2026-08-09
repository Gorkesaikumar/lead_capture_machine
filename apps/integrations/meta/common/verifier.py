"""
Meta Webhook Signature and Verification Token handler.
Provides cryptographic validation of incoming Meta payloads (Instagram and WhatsApp).
"""
import hashlib
import hmac
import logging
from typing import Optional
from django.conf import settings
from apps.integrations.meta.common.exceptions import (
    SignatureVerificationError,
    WebhookVerificationError,
)

logger = logging.getLogger("apps.integrations.meta")


class MetaSignatureVerifier:
    """
    Validates Meta webhook signatures (HMAC-SHA256) and GET challenge tokens.
    """

    @classmethod
    def get_app_secret(cls) -> str:
        return getattr(settings, "META_APP_SECRET", "")

    @classmethod
    def get_verify_token(cls) -> str:
        return getattr(settings, "META_VERIFY_TOKEN", "")

    @classmethod
    def verify_signature(
        cls,
        raw_body: bytes,
        signature_header: Optional[str],
        app_secret: Optional[str] = None,
    ) -> bool:
        """
        Verifies the X-Hub-Signature-256 header sent by Meta using HMAC-SHA256.

        Args:
            raw_body: Raw request body in bytes.
            signature_header: Header value format 'sha256=<hex_digest>'
            app_secret: Meta App Secret (defaults to settings.META_APP_SECRET)

        Returns:
            bool: True if signature matches.

        Raises:
            SignatureVerificationError: If header is missing or signature mismatch.
        """
        secret = app_secret or cls.get_app_secret()
        if not secret:
            logger.error("META_APP_SECRET is not configured in settings.")
            raise SignatureVerificationError("Meta App Secret is not configured.")

        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header on incoming Meta webhook.")
            raise SignatureVerificationError("Missing signature header.")

        prefix = "sha256="
        if not signature_header.startswith(prefix):
            logger.warning("Malformed X-Hub-Signature-256 header format: %s", signature_header[:15])
            raise SignatureVerificationError("Invalid signature header format.")

        expected_hash = signature_header[len(prefix):].strip()

        computed_hash = hmac.new(
            key=secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, expected_hash):
            logger.warning("HMAC-SHA256 signature mismatch on incoming Meta webhook.")
            raise SignatureVerificationError("Signature validation failed.")

        return True

    @classmethod
    def verify_challenge(
        cls,
        mode: Optional[str],
        verify_token: Optional[str],
        challenge: Optional[str],
        expected_token: Optional[str] = None,
    ) -> str:
        """
        Validates Meta webhook GET verification challenge.

        Args:
            mode: Query param hub.mode (must be 'subscribe')
            verify_token: Query param hub.verify_token
            challenge: Query param hub.challenge
            expected_token: Expected verification token (defaults to settings.META_VERIFY_TOKEN)

        Returns:
            str: The challenge string to return in HTTP 200 response.

        Raises:
            WebhookVerificationError: If mode or token is invalid.
        """
        target_token = expected_token or cls.get_verify_token()
        if not target_token:
            logger.error("META_VERIFY_TOKEN is not configured in settings.")
            raise WebhookVerificationError("Meta Verify Token is not configured.")

        if mode != "subscribe":
            logger.warning("Invalid hub.mode in webhook verification: %s", mode)
            raise WebhookVerificationError("Invalid hub.mode. Expected 'subscribe'.")

        if not verify_token or not hmac.compare_digest(verify_token, target_token):
            logger.warning("Invalid hub.verify_token in webhook verification challenge.")
            raise WebhookVerificationError("Verification token mismatch.")

        if not challenge:
            raise WebhookVerificationError("Missing hub.challenge parameter.")

        logger.info("Successfully verified Meta webhook subscription challenge.")
        return challenge

    @classmethod
    def verify_signed_request(cls, signed_request: str, app_secret: Optional[str] = None) -> Optional[dict]:
        """
        Parses and verifies a Meta signed_request.
        Returns the decoded JSON payload if valid, None otherwise.
        """
        import base64
        import json
        
        secret = app_secret or cls.get_app_secret()
        if not secret:
            logger.error("META_APP_SECRET is not configured for signed_request verification.")
            return None

        try:
            encoded_sig, encoded_payload = signed_request.split('.', 1)
        except ValueError:
            logger.warning("Invalid signed_request format (no dot).")
            return None

        def decode_base64_url(data):
            data = data.replace('-', '+').replace('_', '/')
            data += '=' * (4 - (len(data) % 4))
            return base64.b64decode(data)

        try:
            sig = decode_base64_url(encoded_sig)
            payload = json.loads(decode_base64_url(encoded_payload).decode('utf-8'))
        except Exception as e:
            logger.warning(f"Error decoding signed_request: {e}")
            return None

        expected_sig = hmac.new(
            secret.encode('utf-8'),
            encoded_payload.encode('utf-8'),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(expected_sig, sig):
            logger.warning("HMAC-SHA256 signature mismatch on signed_request.")
            return None

        return payload
