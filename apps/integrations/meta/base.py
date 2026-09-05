"""
Core abstractions and standardized message representations for Meta and messaging integrations.
Provides provider-independent data contracts and interfaces.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class NormalizedInboundMessage:
    """
    Normalized, provider-independent representation of an inbound communication event
    originating from Instagram Direct or WhatsApp Cloud API.
    """

    channel: str  # "INSTAGRAM" or "WHATSAPP"
    external_message_id: str
    external_user_id: str
    destination_id: Optional[str] = None
    sender_name: Optional[str] = None
    sender_username: Optional[str] = None
    sender_phone: Optional[str] = None
    text: Optional[str] = None
    message_type: str = "TEXT"  # "TEXT", "IMAGE", "VIDEO", "AUDIO", "DOCUMENT", "OTHER"
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    provider_timestamp: Optional[datetime] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    # Additional account-scoped envelope identity (Instagram entry.id), never sender.id.
    destination_aliases: Tuple[str, ...] = ()

    def to_service_dict(self) -> Dict[str, Any]:
        """
        Converts the normalized message into a dictionary compatible with ConversationService.
        """
        return {
            "channel": self.channel,
            "external_user_id": self.external_user_id,
            "external_message_id": self.external_message_id,
            "destination_id": self.destination_id,
            "display_name": self.sender_name,
            "username": self.sender_username,
            "phone_number": self.sender_phone,
            "text": self.text or "",
            "message_type": self.message_type,
            "attachment_metadata": {"items": self.attachments} if self.attachments else {},
            "provider_timestamp": self.provider_timestamp,
            "raw_payload": self.raw_metadata,
        }


@dataclass(frozen=True)
class OutboundMessage:
    """
    Represents an outbound message payload to be sent to a customer.
    """

    recipient_id: str  # Phone number for WhatsApp, Scoped User ID for Instagram
    text: Optional[str] = None
    message_type: str = "TEXT"
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundResult:
    """
    Result of a message dispatch through a provider adapter.
    """

    success: bool
    external_message_id: Optional[str] = None
    provider_response: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class InboundMessageParser(ABC):
    """
    Interface for parsing raw webhook payloads into NormalizedInboundMessage instances.
    """

    @abstractmethod
    def can_parse(self, payload: Dict[str, Any]) -> bool:
        """
        Determines whether this parser can handle the given raw webhook payload.
        """
        pass

    @abstractmethod
    def parse_messages(self, payload: Dict[str, Any]) -> List[NormalizedInboundMessage]:
        """
        Parses the raw webhook payload and extracts a list of normalized messages.
        """
        pass


class MessagingProvider(ABC):
    """
    Interface for channel messaging providers (Instagram, WhatsApp).
    Handles sending messages to external communication networks.
    """

    @property
    @abstractmethod
    def channel(self) -> str:
        """
        The communication channel name (e.g., 'INSTAGRAM', 'WHATSAPP').
        """
        pass

    @abstractmethod
    def send_text_message(self, recipient_id: str, text: str) -> OutboundResult:
        """
        Sends a plain text message to the recipient.
        """
        pass

    @abstractmethod
    def send_media_message(
        self, recipient_id: str, media_url: str, media_type: str, caption: Optional[str] = None
    ) -> OutboundResult:
        """
        Sends a media attachment (image, video, document) to the recipient.
        """
        pass
