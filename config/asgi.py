"""
ASGI config for Photo Studio CRM.
Exposes the ASGI callable as a module-level variable named ``application``.
Supports HTTP requests via Django ASGI and WebSockets via Django Channels.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing consumers and routing code.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from apps.core.channels_middleware import TokenAuthMiddlewareStack  # noqa: E402
from apps.core.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
