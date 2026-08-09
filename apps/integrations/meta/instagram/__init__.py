"""
Meta Instagram Integration components.
"""
from apps.integrations.meta.instagram.parser import InstagramInboundParser
from apps.integrations.meta.instagram.provider import InstagramMessagingProvider

__all__ = [
    "InstagramInboundParser",
    "InstagramMessagingProvider",
]
