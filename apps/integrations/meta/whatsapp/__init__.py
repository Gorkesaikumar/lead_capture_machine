"""
Meta WhatsApp Cloud API Integration components.
"""
from apps.integrations.meta.whatsapp.parser import WhatsAppInboundParser
from apps.integrations.meta.whatsapp.provider import WhatsAppMessagingProvider

__all__ = [
    "WhatsAppInboundParser",
    "WhatsAppMessagingProvider",
]
