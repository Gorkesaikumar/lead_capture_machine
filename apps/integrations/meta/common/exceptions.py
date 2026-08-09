"""
Exceptions for Meta integration operations.
"""


class MetaIntegrationError(Exception):
    """Base exception for all Meta integration errors."""
    pass


class SignatureVerificationError(MetaIntegrationError):
    """Raised when incoming webhook signature verification fails."""
    pass


class WebhookVerificationError(MetaIntegrationError):
    """Raised when GET webhook challenge verification fails."""
    pass


class PayloadParseError(MetaIntegrationError):
    """Raised when raw payload is malformed or cannot be parsed."""
    pass


from typing import Any, Dict, Optional


class ProviderSendError(MetaIntegrationError):
    """Raised when sending outbound message to Meta Graph API fails."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        subcode: Optional[int] = None,
        raw_error: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.raw_error = raw_error or {}

