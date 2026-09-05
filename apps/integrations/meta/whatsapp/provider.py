"""
WhatsApp Cloud API Messaging Provider Adapter.
Implements outbound communication via Meta WhatsApp Cloud API with strict
enforcement of the 24-hour Customer Service Window policy and approved Template Messages.
"""
import logging
from typing import Any, Dict, List, Optional
from django.conf import settings
from apps.conversations.services import ConversationService
from apps.integrations.meta.base import MessagingProvider, OutboundResult
from apps.integrations.meta.common.client import MetaGraphClient
from apps.integrations.meta.common.exceptions import ProviderSendError
from apps.integrations.meta.whatsapp.templates import WhatsAppTemplateBuilder

logger = logging.getLogger("apps.integrations.meta.whatsapp")


class WhatsAppMessagingProvider(MessagingProvider):
    """
    Messaging provider for WhatsApp Cloud API.
    Handles standard text, media, interactive messages, and approved business templates.
    """

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        client: Optional[MetaGraphClient] = None,
        organization=None,
    ):
        self.organization = organization
        self._phone_number_id = phone_number_id or getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        self._access_token = access_token or getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        self.client = client or MetaGraphClient(access_token=self._access_token)

    @property
    def channel(self) -> str:
        return "WHATSAPP"

    @property
    def phone_number_id(self) -> str:
        return self._phone_number_id

    def is_free_form_permitted(self, recipient_id: str) -> bool:
        """
        Determines whether free-form messaging is permitted under WhatsApp's
        24-hour Customer Service Window policy.
        """
        return ConversationService.is_within_24h_window("WHATSAPP", str(recipient_id).strip(), organization=self.organization)

    def send_text_message(self, recipient_id: str, text: str) -> OutboundResult:
        """
        Sends a standard text message to a WhatsApp recipient phone number.
        Note: WhatsApp Cloud API requires free-form text messages to be within the 24-hour window.
        """
        if not self.phone_number_id:
            logger.error("WHATSAPP_PHONE_NUMBER_ID is not configured in settings.")
            return OutboundResult(success=False, error_message="WhatsApp Phone Number ID is not configured.")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient_id).strip(),
            "type": "text",
            "text": {"preview_url": True, "body": text},
        }

        return self._dispatch_message(payload, recipient_id=recipient_id, message_desc="text message")

    def send_template_message(
        self,
        recipient_id: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> OutboundResult:
        """
        Sends a pre-approved Meta WhatsApp Business Template message.
        Required for initiating conversations or messaging outside the 24-hour customer service window.
        """
        if not self.phone_number_id:
            logger.error("WHATSAPP_PHONE_NUMBER_ID is not configured in settings.")
            return OutboundResult(success=False, error_message="WhatsApp Phone Number ID is not configured.")

        payload = WhatsAppTemplateBuilder.build_template_payload(
            recipient_phone=recipient_id,
            template_name=template_name,
            language_code=language_code,
            components=components,
        )

        return self._dispatch_message(
            payload,
            recipient_id=recipient_id,
            message_desc=f"template message ({template_name})",
        )

    def send_booking_link_message(
        self,
        recipient_id: str,
        booking_url: str,
        customer_name: Optional[str] = None,
        service_name: Optional[str] = None,
        force_template: bool = False,
    ) -> OutboundResult:
        """
        Dispatches a secure booking link to a customer on WhatsApp.
        - If within the 24-hour customer service window: sends free-form formatted message.
        - If outside the 24-hour customer service window: sends approved WhatsApp Template.
        """
        cust_name = customer_name or "Valued Client"
        svc_name = service_name or "Photo Session"

        can_send_free_form = not force_template and self.is_free_form_permitted(recipient_id)

        if can_send_free_form:
            logger.info("24h window active for %s; sending free-form booking link message.", recipient_id)
            body = (
                f"Hello {cust_name}!\n\n"
                f"Here is your private booking link for your {svc_name}:\n"
                f"{booking_url}\n\n"
                f"Please choose your preferred date and time to reserve your appointment."
            )
            return self.send_text_message(recipient_id=recipient_id, text=body)

        logger.info(
            "24h window expired or template forced for %s; using approved WhatsApp template flow.",
            recipient_id,
        )
        template_payload = WhatsAppTemplateBuilder.build_booking_invitation_template(
            recipient_phone=recipient_id,
            booking_url=booking_url,
            customer_name=cust_name,
            service_name=svc_name,
        )

        return self._dispatch_message(
            template_payload,
            recipient_id=recipient_id,
            message_desc="booking link template message",
        )

    def send_booking_confirmation_message(
        self,
        recipient_id: str,
        customer_name: str,
        service_name: str,
        starts_at: str,
    ) -> OutboundResult:
        """
        Sends an approved WhatsApp Business Template for booking confirmation.
        Must be used since confirmations often happen outside the 24-hour window.
        """
        logger.info("Sending booking confirmation template to %s", recipient_id)
        template_payload = WhatsAppTemplateBuilder.build_booking_confirmation_template(
            recipient_phone=recipient_id,
            customer_name=customer_name,
            service_name=service_name,
            datetime_formatted=starts_at,
        )

        return self._dispatch_message(
            template_payload,
            recipient_id=recipient_id,
            message_desc="booking confirmation template message",
        )

    def send_media_message(
        self, recipient_id: str, media_url: str, media_type: str = "IMAGE", caption: Optional[str] = None
    ) -> OutboundResult:
        """
        Sends a hosted media message (image, video, audio, document) to a WhatsApp recipient.
        """
        if not self.phone_number_id:
            logger.error("WHATSAPP_PHONE_NUMBER_ID is not configured in settings.")
            return OutboundResult(success=False, error_message="WhatsApp Phone Number ID is not configured.")

        wa_type = media_type.lower()
        if wa_type not in ["image", "video", "audio", "document"]:
            wa_type = "image"

        media_payload = {"link": media_url}
        if caption and wa_type in ["image", "video", "document"]:
            media_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient_id).strip(),
            "type": wa_type,
            wa_type: media_payload,
        }

        return self._dispatch_message(payload, recipient_id=recipient_id, message_desc=f"media ({wa_type})")

    def _dispatch_message(
        self, payload: Dict[str, Any], recipient_id: str, message_desc: str = "message"
    ) -> OutboundResult:
        """
        Executes HTTP POST to WhatsApp Cloud API and standardizes the response.
        """
        endpoint = f"{self.phone_number_id}/messages"

        try:
            response = self.client.post(endpoint, payload, access_token=self._access_token)
            messages = response.get("messages", [])
            message_id = messages[0].get("id") if messages else None
            logger.info("Sent WhatsApp %s to %s (wamid=%s)", message_desc, recipient_id, message_id)
            return OutboundResult(
                success=bool(message_id),
                error_message=None if message_id else "Meta returned no message ID; acceptance is unconfirmed.",
                external_message_id=message_id,
                provider_response=response,
            )
        except ProviderSendError as exc:
            logger.error("Failed to send WhatsApp %s to %s: %s", message_desc, recipient_id, str(exc))
            return OutboundResult(
                success=False,
                error_message=str(exc),
            )
