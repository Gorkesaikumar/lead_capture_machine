"""
Instagram Messaging Provider Adapter.
Implements outbound communication via Meta Instagram Messaging Graph API.
Supports text messaging, media messaging, and structured booking-link templates.
"""
import logging
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
from apps.integrations.meta.base import MessagingProvider, OutboundResult
from apps.integrations.meta.common.client import MetaGraphClient, mask_token
from apps.integrations.meta.common.exceptions import ProviderSendError

logger = logging.getLogger("apps.integrations.meta.instagram")


class InstagramMessagingProvider(MessagingProvider):
    """
    Messaging provider for Instagram Direct.
    Dispatches outbound messages using the Meta Graph API /me/messages endpoint.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        client: Optional[MetaGraphClient] = None,
        account_id: str = "me",
    ):
        self._access_token = access_token or getattr(settings, "INSTAGRAM_ACCESS_TOKEN", "")
        self.account_id = account_id
        self.client = client or MetaGraphClient(access_token=self._access_token, graph_host="graph.instagram.com")

    @property
    def channel(self) -> str:
        return "INSTAGRAM"

    @classmethod
    def validate_recipient_id(cls, recipient_id: Any) -> Tuple[bool, Optional[str]]:
        """
        Validates whether recipient_id is a plausible Instagram-scoped user ID (IGSID).
        Prevents sending internal UUIDs, phone numbers, or dummy mock identifiers to Meta API.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not recipient_id:
            return False, "Instagram recipient ID cannot be empty."

        rec_str = str(recipient_id).strip()
        if not rec_str:
            return False, "Instagram recipient ID cannot be blank."

        # Check for placeholder/mock strings from test data
        if rec_str.lower() in ["user_a", "user_b", "unknown", "null", "none", "placeholder", "test"]:
            return (
                False,
                f"Invalid Instagram recipient ID '{rec_str}'. A real customer Instagram message must be received first.",
            )

        # Check if accidentally passed a Django UUID (length 36, contains 4 hyphens)
        if len(rec_str) == 36 and rec_str.count("-") == 4:
            return (
                False,
                "Invalid recipient ID: an internal database UUID was provided instead of an Instagram-scoped user ID (IGSID).",
            )

        # Check if accidentally passed an email address
        if "@" in rec_str:
            return (
                False,
                "Invalid recipient ID: an email address was provided instead of an Instagram-scoped user ID (IGSID).",
            )

        # Check if accidentally passed a phone number with plus sign
        if rec_str.startswith("+"):
            return (
                False,
                "Invalid recipient ID: a phone number was provided instead of an Instagram-scoped user ID (IGSID).",
            )

        return True, None

    def _format_provider_error(self, exc: ProviderSendError) -> str:
        """
        Translates raw Meta Graph API errors into clear, actionable, user-friendly messages.
        """
        code = getattr(exc, "code", None)
        subcode = getattr(exc, "subcode", None)
        msg = str(exc)

        # Param recipient[id] invalid / missing / non-numeric
        if code == 100 or "Param recipient[id]" in msg or "valid ID string" in msg:
            return (
                "Unable to deliver message: The customer's Instagram account ID is invalid or cannot receive messages. "
                "The customer must send a new Instagram DM to the studio first."
            )

        # Authentication / Token expired errors
        if code in (10, 190) or "Error validating access token" in msg or "Session has expired" in msg:
            return (
                "Instagram integration authentication expired. Please re-authenticate your Instagram account in Settings."
            )

        # Messaging window closed (e.g. 24-hour policy)
        if code == 230 or subcode in (2018278, 2018001) or "window" in msg.lower() or "24-hour" in msg.lower():
            return (
                "Instagram's 24-hour messaging window has expired. "
                "The customer must send a new message before you can reply."
            )

        # User cannot receive messages / blocked
        if code == 551 or "User cannot receive messages" in msg:
            return (
                "This Instagram user cannot receive direct messages or has blocked messages from this account."
            )

        # Rate limiting
        if code in (4, 17, 32, 613):
            return "Instagram messaging rate limit reached. Please wait a few moments and try again."

        return msg

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the user's profile details (name, profile_pic) from the Meta Graph API.
        This uses the Instagram-scoped user ID (IGSID).
        """
        is_valid, _ = self.validate_recipient_id(user_id)
        if not is_valid:
            return None

        try:
            response = self.client.get(
                endpoint=str(user_id).strip(),
                params={"fields": "name,username,profile_pic"},
                access_token=self._access_token,
            )
            return response
        except Exception as exc:
            logger.warning("Failed to fetch Instagram user profile for %s: %s", user_id, str(exc))
            return None

    def send_text_message(self, recipient_id: str, text: str) -> OutboundResult:
        """
        Sends a standard direct text message to an Instagram-scoped user ID (IGSID).

        Args:
            recipient_id: Instagram-scoped user ID (IGSID)
            text: Plain text message content

        Returns:
            OutboundResult: Contains success status and provider message ID.
        """
        is_valid, validation_err = self.validate_recipient_id(recipient_id)
        if not is_valid:
            return OutboundResult(success=False, error_message=validation_err)

        clean_text = str(text or "").strip()
        if not clean_text:
            return OutboundResult(success=False, error_message="Text cannot be empty.")

        clean_recipient = str(recipient_id).strip()
        payload = {
            "recipient": {"id": clean_recipient},
            "message": {"text": clean_text},
        }

        logger.info(
            "Dispatching Instagram text message to recipient %s [token=%s]",
            clean_recipient,
            mask_token(self._access_token),
        )

        try:
            response = self.client.post(f"{self.account_id}/messages", payload, access_token=self._access_token)
            message_id = response.get("message_id")
            logger.info("Successfully sent Instagram message to %s (mid=%s)", clean_recipient, message_id)
            return OutboundResult(
                success=bool(message_id),
                error_message=None if message_id else "Meta returned no message ID; acceptance is unconfirmed.",
                external_message_id=message_id,
                provider_response=response,
            )
        except ProviderSendError as exc:
            logger.error("Failed to send Instagram text message to %s: %s", clean_recipient, str(exc))
            friendly_err = self._format_provider_error(exc)
            return OutboundResult(
                success=False,
                error_message=friendly_err,
            )

    def send_booking_link_message(
        self,
        recipient_id: str,
        booking_url: str,
        customer_name: Optional[str] = None,
        service_name: Optional[str] = None,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        fallback_text: Optional[str] = None,
        **kwargs: Any,
    ) -> OutboundResult:
        """
        Sends a booking link to the customer via Instagram Direct.
        Attempts to send a rich CTA button template first; falls back to formatted text message.

        Args:
            recipient_id: Instagram-scoped user ID (IGSID)
            booking_url: Secure public booking link URL (e.g., https://studio.com/book/<token>)
            customer_name: Optional customer display name
            service_name: Optional service name
            title: Optional title for the template card
            subtitle: Optional subtitle description
            fallback_text: Optional text message body override

        Returns:
            OutboundResult
        """
        is_valid, validation_err = self.validate_recipient_id(recipient_id)
        if not is_valid:
            return OutboundResult(success=False, error_message=validation_err)

        card_title = title or (f"Book {service_name}" if service_name else "Select Your Photo Session Slot")
        card_subtitle = (
            subtitle
            or "Click the button below to choose your preferred appointment date and time."
        )

        clean_recipient = str(recipient_id).strip()

        # 1. Try sending structured CTA button template
        template_payload = {
            "recipient": {"id": clean_recipient},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "generic",
                        "elements": [
                            {
                                "title": card_title[:80],
                                "subtitle": card_subtitle[:80],
                                "buttons": [
                                    {
                                        "type": "web_url",
                                        "url": booking_url,
                                        "title": "Book Appointment",
                                    }
                                ],
                            }
                        ],
                    },
                }
            },
        }

        try:
            response = self.client.post(f"{self.account_id}/messages", template_payload, access_token=self._access_token)
            message_id = response.get("message_id")
            logger.info("Sent Instagram booking-link template to %s (mid=%s)", clean_recipient, message_id)
            return OutboundResult(
                success=bool(message_id),
                error_message=None if message_id else "Meta returned no message ID; acceptance is unconfirmed.",
                external_message_id=message_id,
                provider_response=response,
            )
        except ProviderSendError as exc:
            logger.warning(
                "Failed to send Instagram rich template to %s (%s). Falling back to plain text URL.",
                clean_recipient,
                str(exc),
            )
            # Fallback to plain text message containing the booking link
            greeting = f"Hi {customer_name}! 👋\n\n" if customer_name else "Hi! 👋\n\n"
            plain_text = (
                fallback_text
                or f"{greeting}{card_title}\n{card_subtitle}\n\nBook here: {booking_url}"
            )
            return self.send_text_message(recipient_id=clean_recipient, text=plain_text)

    def send_media_message(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str = "IMAGE",
        caption: Optional[str] = None,
    ) -> OutboundResult:
        """
        Sends a media attachment (image, video, etc.) to an Instagram user.
        """
        is_valid, validation_err = self.validate_recipient_id(recipient_id)
        if not is_valid:
            return OutboundResult(success=False, error_message=validation_err)

        clean_recipient = str(recipient_id).strip()
        ig_type = media_type.lower()
        if ig_type not in ["image", "video", "audio", "file"]:
            ig_type = "image"

        payload = {
            "recipient": {"id": clean_recipient},
            "message": {
                "attachment": {
                    "type": ig_type,
                    "payload": {"url": media_url, "is_reusable": True},
                }
            },
        }

        try:
            response = self.client.post(f"{self.account_id}/messages", payload, access_token=self._access_token)
            message_id = response.get("message_id")
            logger.info("Sent Instagram media message (%s) to %s (mid=%s)", ig_type, clean_recipient, message_id)
            return OutboundResult(
                success=bool(message_id),
                error_message=None if message_id else "Meta returned no message ID; acceptance is unconfirmed.",
                external_message_id=message_id,
                provider_response=response,
            )
        except ProviderSendError as exc:
            logger.error("Failed to send Instagram media to %s: %s", clean_recipient, str(exc))
            friendly_err = self._format_provider_error(exc)
            return OutboundResult(
                success=False,
                error_message=friendly_err,
            )

