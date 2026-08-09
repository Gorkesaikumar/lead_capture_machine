"""
WhatsApp Cloud API Template Message Builders.
Constructs compliant Meta WhatsApp Business template payloads for out-of-session messaging.
"""
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
from django.conf import settings

logger = logging.getLogger("apps.integrations.meta.whatsapp")


@dataclass
class WhatsAppTemplateParameter:
    """
    Represents a parameter within a template component.
    """
    type: str = "text"
    text: Optional[str] = None
    image_url: Optional[str] = None
    document_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        if self.type == "text":
            return {"type": "text", "text": self.text or ""}
        elif self.type == "image":
            return {"type": "image", "image": {"link": self.image_url}}
        elif self.type == "document":
            return {"type": "document", "document": {"link": self.document_url}}
        return {"type": self.type, "text": self.text or ""}


@dataclass
class WhatsAppTemplateComponent:
    """
    Represents a template component (header, body, button).
    """
    type: str  # "header", "body", "button"
    sub_type: Optional[str] = None  # "url", "quick_reply" for buttons
    index: Optional[str] = None  # Position index for button components (e.g. "0")
    parameters: List[WhatsAppTemplateParameter] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": self.type,
            "parameters": [param.to_dict() for param in self.parameters],
        }
        if self.sub_type:
            data["sub_type"] = self.sub_type
        if self.index is not None:
            data["index"] = str(self.index)
        return data


class WhatsAppTemplateBuilder:
    """
    Builder utility for constructing Meta-compliant WhatsApp template message payloads.
    """

    @classmethod
    def build_template_payload(
        cls,
        recipient_phone: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Builds raw Meta WhatsApp template payload.
        """
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(recipient_phone).strip(),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        return payload

    @classmethod
    def build_booking_invitation_template(
        cls,
        recipient_phone: str,
        booking_url: str,
        customer_name: Optional[str] = None,
        service_name: Optional[str] = None,
        template_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds an approved booking invitation template payload.
        Passes customer name, service name, and booking URL / CTA parameters.
        """
        tpl_name = template_name or getattr(settings, "WHATSAPP_BOOKING_TEMPLATE_NAME", "studio_booking_invitation")
        lang = language_code or getattr(settings, "WHATSAPP_DEFAULT_LANGUAGE", "en")
        cust_name = customer_name or "Valued Client"
        svc_name = service_name or "Photo Session"

        # Extract url suffix if the template button has dynamic URL variable
        url_suffix = booking_url.replace("https://", "").replace("http://", "")

        components = [
            WhatsAppTemplateComponent(
                type="body",
                parameters=[
                    WhatsAppTemplateParameter(type="text", text=cust_name),
                    WhatsAppTemplateParameter(type="text", text=svc_name),
                ],
            ).to_dict(),
            WhatsAppTemplateComponent(
                type="button",
                sub_type="url",
                index="0",
                parameters=[
                    WhatsAppTemplateParameter(type="text", text=url_suffix),
                ],
            ).to_dict(),
        ]

        return cls.build_template_payload(
            recipient_phone=recipient_phone,
            template_name=tpl_name,
            language_code=lang,
            components=components,
        )

    @classmethod
    def build_booking_confirmation_template(
        cls,
        recipient_phone: str,
        customer_name: str,
        service_name: str,
        datetime_formatted: str,
        template_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds an approved booking confirmation template payload.
        Passes customer name, service name, and formatted date/time.
        """
        tpl_name = template_name or getattr(settings, "WHATSAPP_BOOKING_CONFIRMATION_TEMPLATE_NAME", "studio_booking_confirmation")
        lang = language_code or getattr(settings, "WHATSAPP_DEFAULT_LANGUAGE", "en")

        components = [
            WhatsAppTemplateComponent(
                type="body",
                parameters=[
                    WhatsAppTemplateParameter(type="text", text=customer_name),
                    WhatsAppTemplateParameter(type="text", text=service_name),
                    WhatsAppTemplateParameter(type="text", text=datetime_formatted),
                ],
            ).to_dict()
        ]

        return cls.build_template_payload(
            recipient_phone=recipient_phone,
            template_name=tpl_name,
            language_code=lang,
            components=components,
        )
