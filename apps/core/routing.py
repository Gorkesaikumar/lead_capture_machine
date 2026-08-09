"""
WebSocket URL routing configuration for Django Channels.
Maps WebSocket endpoints to their corresponding async consumers.
"""
from django.urls import re_path
from apps.core.consumers import (
    AdminDashboardConsumer,
    ConversationConsumer,
    LeadConsumer,
)

websocket_urlpatterns = [
    # Admin dashboard global stream
    re_path(r"^ws/admin/dashboard/?$", AdminDashboardConsumer.as_asgi()),
    re_path(r"^ws/dashboard/?$", AdminDashboardConsumer.as_asgi()),
    re_path(r"^ws/admin/?$", AdminDashboardConsumer.as_asgi()),

    # Conversation specific stream
    re_path(r"^ws/admin/conversations/(?P<conversation_id>[^/]+)/?$", ConversationConsumer.as_asgi()),
    re_path(r"^ws/conversations/(?P<conversation_id>[^/]+)/?$", ConversationConsumer.as_asgi()),

    # Lead specific stream
    re_path(r"^ws/admin/leads/(?P<lead_id>[^/]+)/?$", LeadConsumer.as_asgi()),
    re_path(r"^ws/leads/(?P<lead_id>[^/]+)/?$", LeadConsumer.as_asgi()),
]
