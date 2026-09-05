"""
WebSocket Authentication Middleware for Django Channels.
Authenticates incoming WebSocket handshakes using DRF Token Authentication.
Supports tokens supplied via query parameter (?token=...) or Authorization header.
Strictly ensures only authenticated and active admin/staff users are permitted.
"""
import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

logger = logging.getLogger("apps.core.channels")


@database_sync_to_async
def get_user_from_token(token_key: str):
    """
    Look up user associated with DRF token.
    Enforces active status and staff privileges for admin WebSocket access.
    """
    if not token_key:
        return AnonymousUser()
    try:
        token = Token.objects.select_related("user").get(key=token_key)
        user = token.user
        if user.is_active:
            return user
        logger.warning("WebSocket auth rejected: user id=%s is inactive or not staff", user.id)
        return AnonymousUser()
    except Token.DoesNotExist:
        logger.warning("WebSocket auth rejected: invalid or expired token")
        return AnonymousUser()
    except Exception as exc:
        logger.exception("Error authenticating WebSocket token: %s", exc)
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom Channels middleware to authenticate WebSocket connections via DRF Token.
    """

    async def __call__(self, scope, receive, send):
        # Only process websocket connections
        if scope["type"] == "websocket":
            token_key = next((p.removeprefix("token.") for p in scope.get("subprotocols", []) if p.startswith("token.")), None)

            # 1. Try parsing token from query string (e.g. ws://host/ws/...?token=<key>)
            query_string = scope.get("query_string", b"").decode("utf-8")
            if query_string and not token_key:
                parsed_query = parse_qs(query_string)
                token_list = parsed_query.get("token")
                if token_list and len(token_list) > 0:
                    token_key = token_list[0].strip()

            # 2. Fallback to Authorization / Sec-WebSocket-Protocol headers if not in query string
            if not token_key and "headers" in scope:
                headers = dict(scope["headers"])
                auth_header = headers.get(b"authorization", b"").decode("utf-8")
                if auth_header.startswith("Token "):
                    token_key = auth_header.split("Token ", 1)[1].strip()

            if token_key:
                scope["auth_token_key"] = token_key
                scope["user"] = await get_user_from_token(token_key)
            else:
                logger.warning("WebSocket auth rejected: Missing Token in query string and Authorization header")
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    """
    Helper stack wrapping TokenAuthMiddleware.
    """
    return TokenAuthMiddleware(inner)
