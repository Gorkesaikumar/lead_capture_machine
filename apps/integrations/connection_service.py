"""Verified Meta onboarding. Credentials and provider bodies never reach clients/logs."""
import hashlib
import hmac
import ipaddress
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.db import transaction, connection
from django.utils import timezone
from apps.core.utils.crypto import encrypt_string
from .models import IntegrationConfig, OAuthAttempt, DataDeletionRequest
from apps.organizations.models import Organization, OrganizationMembership

logger = logging.getLogger("apps.integrations.connections")
SCOPES = {"INSTAGRAM": ["instagram_business_basic", "instagram_business_manage_messages"],
          "WHATSAPP": ["whatsapp_business_management", "whatsapp_business_messaging"]}
ERRORS = {
    "invalid_state": "This connection request expired or was already used. Start again from Channels.",
    "authorization_cancelled": "Connection was cancelled. You can connect again when ready.",
    "permission_required": "Required Meta permissions were not granted. Reconnect and approve the requested permissions.",
    "token_expired": "Meta rejected or expired the token. Reconnect this channel.",
    "token_exchange_failed": "Meta could not complete authorization. Start the connection again.",
    "no_instagram_account": "No accessible Instagram Professional account was found. Use a Business or Creator account.",
    "no_waba_or_phone_found": "No eligible WhatsApp account and phone were shared. Complete Meta onboarding with a phone number.",
    "asset_not_authorized": "The selected WhatsApp account or phone was not authorized for this connection.",
    "account_already_connected_to_another_workspace": "This account is already connected to another workspace.",
    "disconnect_before_replacing": "Disconnect the current account before connecting a different account.",
    "webhook_subscription_failed": "Meta could not confirm the webhook subscription. Check the app's webhook configuration and reconnect.",
    "phone_registration_failed": "Meta could not register this phone. Check its verification and two-step verification settings in WhatsApp Manager, then reconnect.",
    "rate_limited": "Meta temporarily limited requests. Please wait and try again.",
    "meta_connection_failed": "Meta could not be reached. Please try again shortly.",
    "configuration_required": "The administrator must configure this Meta connection before onboarding can start.",
    "data_deletion_pending": "Account data deletion is still running. Try connecting again after it finishes.",
}


class OAuthFailure(Exception):
    def __init__(self, code):
        self.code = code if code in ERRORS else "meta_connection_failed"
        super().__init__(self.code)


def app_credentials(provider):
    if provider == "INSTAGRAM":
        return (getattr(settings, "META_INSTAGRAM_APP_ID", "") or settings.META_APP_ID,
                getattr(settings, "META_INSTAGRAM_APP_SECRET", "") or settings.META_APP_SECRET)
    return settings.META_APP_ID, settings.META_APP_SECRET


def graph_base(provider):
    version = settings.META_GRAPH_API_VERSION
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise OAuthFailure("configuration_required")
    host = "graph.instagram.com" if provider == "INSTAGRAM" else "graph.facebook.com"
    return f"https://{host}/{version}"


def meta_request(method, url, token=None, failure="meta_connection_failed", **kwargs):
    try:
        response = getattr(requests, method)(url, headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=settings.META_HTTP_TIMEOUT_SECONDS, **kwargs)
        body = response.json()
        if not isinstance(body, dict):
            raise OAuthFailure(failure)
        if response.status_code >= 400 or body.get("error"):
            error = body.get("error", {})
            code = error.get("code") if isinstance(error, dict) else None
            reason = ("token_expired" if code == 190 else "permission_required" if code in (10, 200)
                      else "rate_limited" if response.status_code == 429 or code in (4, 17, 32, 613, 130429) else failure)
            logger.warning("meta_request_failed", extra={"provider_code": code, "http_status": response.status_code, "reason": reason})
            raise OAuthFailure(reason)
        return body
    except (requests.RequestException, ValueError, TypeError):
        raise OAuthFailure(failure) from None


def validate_public_url(uri, path):
    """Validate without rewriting: Meta compares the exact registered URI."""
    try:
        parsed = urlparse(uri)
        host = (parsed.hostname or "").rstrip(".").lower()
        port = parsed.port  # Also reject malformed/out-of-range ports.
        local = host == "localhost" or host.endswith(".localhost")
        try:
            local = local or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        tunnel = any(label in ("ngrok", "ngrok-free") for label in host.split("."))
        if (not host or parsed.username is not None or parsed.password is not None
                or parsed.path != path or parsed.params or parsed.query or parsed.fragment
                or "?" in uri or "#" in uri or "\\" in uri or any(c.isspace() for c in uri)
                or (port is not None and port == 0)
                or parsed.scheme not in ("http", "https")
                or (parsed.scheme == "http" and not (settings.DEBUG and local))
                or (not settings.DEBUG and (local or tunnel))):
            raise ValueError("Invalid public URL")
    except (ValueError, TypeError):
        raise OAuthFailure("configuration_required") from None
    return uri


def frontend_return_uri():
    origin = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    validate_public_url(origin, "")
    return origin + "/app/settings/channels"


def callback_uri(request, provider):
    from django.urls import reverse
    configured = getattr(settings, f"META_{provider}_REDIRECT_URI", "")
    path = reverse(f"api_v1:integrations:oauth-{provider.lower()}-callback")
    base = getattr(settings, "META_REDIRECT_BASE_URL", "").rstrip("/")
    if configured:
        uri = configured
    elif base:
        validate_public_url(base, "")
        uri = base + path
    elif settings.DEBUG:
        uri = request.build_absolute_uri(path)
    else:
        # A reverse proxy's Host header must never choose production OAuth identity.
        raise OAuthFailure("configuration_required")
    return validate_public_url(uri, path)


def create_attempt(user, organization, provider, redirect_uri=""):
    state = secrets.token_urlsafe(32)
    OAuthAttempt.objects.create(state_hash=hashlib.sha256(state.encode()).hexdigest(), user=user,
        organization=organization, provider=provider, redirect_uri=redirect_uri, expires_at=timezone.now()+timedelta(minutes=10))
    logger.info("oauth_started", extra={"provider": provider, "organization_id": str(organization.pk), "user_id": str(user.pk)})
    return state


@transaction.atomic
def consume_attempt(state, provider, user=None, organization=None):
    if not isinstance(state, str) or not 20 <= len(state) <= 128:
        raise OAuthFailure("invalid_state")
    attempt = OAuthAttempt.objects.select_for_update().filter(state_hash=hashlib.sha256(state.encode()).hexdigest(),
        provider=provider, consumed_at__isnull=True, expires_at__gt=timezone.now()).first()
    if not attempt or (user and attempt.user_id != user.pk) or (organization and attempt.organization_id != organization.pk):
        raise OAuthFailure("invalid_state")
    if not OrganizationMembership.objects.filter(user_id=attempt.user_id, organization_id=attempt.organization_id,
            user__is_active=True, is_active=True, role__in=["OWNER", "ADMIN"],
            organization__is_active=True, organization__is_deleted=False).exists():
        raise OAuthFailure("invalid_state")
    attempt.consumed_at = timezone.now()
    attempt.save(update_fields=["consumed_at", "updated_at"])
    return attempt


def require_scopes(scopes, provider):
    if not set(SCOPES[provider]).issubset(set(scopes)):
        raise OAuthFailure("permission_required")


def assert_available(organization, provider, destination, aliases=()):
    with connection.cursor() as cursor:
        for identifier in sorted({destination, *aliases} - {""}):
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [f"{provider}:{identifier}"])
    if provider == "INSTAGRAM":
        from apps.integrations.meta.instagram.identity import matching_configs
        matches = matching_configs((destination, *aliases))
    else:
        matches = IntegrationConfig.objects.filter(provider=provider, is_active=True, metadata__destination_id=destination)
    if matches.exclude(organization=organization).exists():
        raise OAuthFailure("account_already_connected_to_another_workspace")
    current = IntegrationConfig.objects.filter(provider=provider, organization=organization, is_active=True).first()
    if current and current.metadata.get("destination_id") not in (None, destination):
        raise OAuthFailure("disconnect_before_replacing")
    if DataDeletionRequest.objects.filter(status="PENDING", scopes__contains=[{"organization": str(organization.pk)}]).exists():
        raise OAuthFailure("data_deletion_pending")


def save_connection(organization, user, provider, token, metadata, extra_credentials=None):
    now = timezone.now().isoformat()
    config, _ = IntegrationConfig.objects.update_or_create(organization=organization, provider=provider, defaults={
        "is_active": True, "connected_by": user,
        "credentials": {"access_token": encrypt_string(token), **(extra_credentials or {})},
        "metadata": {**metadata, "connected_at": now, "last_verified_at": now, "webhook_subscribed": True,
                     "error_code": "", "last_error": ""}})
    logger.info("integration_connected", extra={"provider": provider, "organization_id": str(organization.pk)})
    return config


def instagram_connect(organization, code, redirect_uri, user=None):
    app_id, secret = app_credentials("INSTAGRAM")
    data = meta_request("post", "https://api.instagram.com/oauth/access_token", failure="token_exchange_failed", data={
        "client_id": app_id, "client_secret": secret, "grant_type": "authorization_code", "redirect_uri": redirect_uri, "code": code})
    if isinstance(data.get("data"), list) and data["data"]:
        data = data["data"][0]
    if not isinstance(data, dict) or not isinstance(data.get("access_token"), str) or not data["access_token"].strip():
        raise OAuthFailure("token_exchange_failed")
    # OAuth's identifier can differ from the Professional account exposed by /me.
    oauth_user_id = str(data.get("user_id") or "")
    token = data["access_token"]
    base = graph_base("INSTAGRAM")
    # Instagram Login must not depend on the Facebook-style user permissions edge.
    # Check grants when returned by the token exchange; absence is not proof of grants.
    scopes = []
    if "permissions" in data:
        permissions = data["permissions"]
        if isinstance(permissions, str):
            permissions = [scope.strip() for scope in permissions.split(",") if scope.strip()]
        if not isinstance(permissions, list) or any(not isinstance(scope, str) for scope in permissions):
            raise OAuthFailure("permission_required")
        require_scopes(permissions, "INSTAGRAM")
        scopes = permissions
    long_lived = meta_request("get", "https://graph.instagram.com/access_token", failure="token_exchange_failed",
        params={"grant_type": "ig_exchange_token", "client_secret": secret, "access_token": token})
    if not isinstance(long_lived.get("access_token"), str) or not long_lived["access_token"].strip():
        raise OAuthFailure("token_exchange_failed")
    try:
        lifetime = long_lived.get("expires_in")
        if isinstance(lifetime, bool) or not isinstance(lifetime, (int, str)) or int(lifetime) <= 0:
            raise ValueError
        expires = timezone.now()+timedelta(seconds=int(lifetime))
    except (ValueError, TypeError, OverflowError):
        raise OAuthFailure("token_exchange_failed") from None
    token = long_lived["access_token"]
    profile = meta_request("get", f"{base}/me", token, failure="no_instagram_account",
        params={"fields": "id,user_id,username,name,profile_picture_url"})
    professional_account_id = str(profile.get("user_id") or profile.get("id") or "")
    from apps.integrations.meta.instagram.identity import account_id
    profile_id = account_id(profile.get("id"))
    if (not isinstance(profile.get("username"), str) or not profile["username"].strip()
            or not re.fullmatch(r"[1-9][0-9]{0,31}", professional_account_id)):
        raise OAuthFailure("no_instagram_account")
    with transaction.atomic():
        list(IntegrationConfig.objects.select_for_update().filter(organization=organization, provider="INSTAGRAM"))
        Organization.objects.select_for_update().get(pk=organization.pk)
        assert_available(organization, "INSTAGRAM", professional_account_id, aliases=(profile_id,))
        subscribed = meta_request("post", f"{base}/{professional_account_id}/subscribed_apps", token, failure="webhook_subscription_failed",
            data={"subscribed_fields": "messages,messaging_seen"})
        if subscribed.get("success") not in (True, "true"):
            raise OAuthFailure("webhook_subscription_failed")
        return save_connection(organization, user, "INSTAGRAM", token, {
            "destination_id": professional_account_id, "account_id": professional_account_id,
            # Both IDs originate from the same authenticated /me response, not webhook guesses.
            "profile_id": profile_id,
            "oauth_user_id": oauth_user_id, "username": profile["username"].strip(), "name": profile.get("name", ""),
            "profile_picture_url": profile.get("profile_picture_url", ""), "scopes": scopes,
            "requested_scopes": list(SCOPES["INSTAGRAM"]),
            "scopes_source": "token_response" if "permissions" in data else "not_returned",
            "token_expires_at": expires.isoformat(), "auth_architecture": "instagram_login"})


def whatsapp_connect(attempt, code, waba_id, phone_id):
    base = graph_base("WHATSAPP")
    app_id, secret = app_credentials("WHATSAPP")
    data = meta_request("get", f"{base}/oauth/access_token", failure="token_exchange_failed",
        params={"client_id": app_id, "client_secret": secret, "code": code})
    token = data.get("access_token")
    if not token:
        raise OAuthFailure("token_exchange_failed")
    debug = meta_request("get", f"{base}/debug_token", f"{app_id}|{secret}", params={"input_token": token}).get("data", {})
    if not debug.get("is_valid") or str(debug.get("app_id")) != app_id:
        raise OAuthFailure("token_expired")
    scopes = debug.get("scopes", [])
    require_scopes(scopes, "WHATSAPP")
    authorized = {str(target) for scope in debug.get("granular_scopes", [])
        if scope.get("scope") == "whatsapp_business_management" for target in scope.get("target_ids", [])}
    if waba_id not in authorized:
        raise OAuthFailure("asset_not_authorized")
    waba = meta_request("get", f"{base}/{waba_id}", token, params={"fields": "id,name,owner_business_info"})
    phone, after = None, None
    for _ in range(20):
        page = meta_request("get", f"{base}/{waba_id}/phone_numbers", token,
            params={"fields": "id,display_phone_number,verified_name,status,code_verification_status", "limit": 100, **({"after": after} if after else {})})
        phone = next((p for p in page.get("data", []) if str(p.get("id")) == phone_id), None)
        if phone or not page.get("paging", {}).get("next"):
            break
        after = page.get("paging", {}).get("cursors", {}).get("after")
        if not after:
            break
    if not phone:
        raise OAuthFailure("asset_not_authorized")
    if not phone.get("display_phone_number"):
        raise OAuthFailure("no_waba_or_phone_found")
    expiry_values = [int(debug[k]) for k in ("expires_at", "data_access_expires_at") if debug.get(k)]
    expiry = datetime.fromtimestamp(min(expiry_values), tz=dt_timezone.utc) if expiry_values else None
    if expiry and expiry <= timezone.now():
        raise OAuthFailure("token_expired")
    organization = attempt.organization
    with transaction.atomic():
        list(IntegrationConfig.objects.select_for_update().filter(organization=organization, provider="WHATSAPP"))
        Organization.objects.select_for_update().get(pk=organization.pk)
        assert_available(organization, "WHATSAPP", phone_id)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [f"WHATSAPP-WABA:{waba_id}"])
        extra = {}
        if phone.get("status") != "CONNECTED":
            # Stable per phone: a failed response/reconnect must not lose its two-step PIN.
            digest = hmac.new(settings.SECRET_KEY.encode(), f"whatsapp-registration:{phone_id}".encode(), hashlib.sha256).digest()
            pin = f"{int.from_bytes(digest[:8], 'big') % 1000000:06d}"
            registered = meta_request("post", f"{base}/{phone_id}/register", token, failure="phone_registration_failed",
                json={"messaging_product": "whatsapp", "pin": pin})
            if registered.get("success") not in (True, "true"):
                raise OAuthFailure("phone_registration_failed")
            extra["registration_pin"] = encrypt_string(pin)
        subscribed = meta_request("post", f"{base}/{waba_id}/subscribed_apps", token, failure="webhook_subscription_failed")
        if subscribed.get("success") not in (True, "true"):
            raise OAuthFailure("webhook_subscription_failed")
        return save_connection(organization, attempt.user, "WHATSAPP", token, {
            "destination_id": phone_id, "phone_number_id": phone_id, "waba_id": waba_id,
            "business_id": str(waba.get("owner_business_info", {}).get("id", "")),
            "display_phone_number": phone["display_phone_number"], "verified_name": phone.get("verified_name", ""),
            "name": waba.get("name", ""), "scopes": scopes,
            "token_expires_at": expiry.isoformat() if expiry else None, "auth_architecture": "embedded_signup"}, extra)


@transaction.atomic
def disconnect(organization, provider):
    config = IntegrationConfig.objects.select_for_update().filter(organization=organization, provider=provider).first()
    if not config:
        return
    Organization.objects.select_for_update().get(pk=organization.pk)
    try:
        token = config.get_credential("access_token")
        asset = config.metadata.get("account_id") if provider == "INSTAGRAM" else config.metadata.get("waba_id")
        if provider == "WHATSAPP" and asset:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [f"WHATSAPP-WABA:{asset}"])
        shared = provider == "WHATSAPP" and IntegrationConfig.objects.filter(provider=provider, is_active=True, metadata__waba_id=asset).exclude(pk=config.pk).exists()
        if token and asset and not shared:
            meta_request("delete", f"{graph_base(provider)}/{asset}/subscribed_apps", token)
    except Exception:
        logger.warning("remote_unsubscribe_unconfirmed", extra={"provider": provider, "organization_id": str(organization.pk)})
    config.is_active = False
    config.credentials = {}
    config.metadata = {**config.metadata, "webhook_subscribed": False, "disconnected_at": timezone.now().isoformat()}
    config.save(update_fields=["is_active", "credentials", "metadata", "updated_at"])
    logger.info("integration_disconnected", extra={"provider": provider, "organization_id": str(organization.pk)})
