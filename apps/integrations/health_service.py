"""Live account and subscription checks, including Instagram long-lived token refresh."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import IntegrationConfig
from .connection_service import meta_request, graph_base, app_credentials, OAuthFailure, ERRORS, require_scopes
from apps.core.utils.crypto import encrypt_string


def verify_integration(config_id):
    config = IntegrationConfig.objects.filter(pk=config_id, is_active=True).first()
    if not config:
        return
    updates, credentials = {}, dict(config.credentials)
    try:
        token = config.get_credential("access_token")
        account = config.metadata.get("destination_id")
        if not token or not account:
            raise OAuthFailure("configuration_required")
        base = graph_base(config.provider)
        expiry = parse_datetime(config.metadata.get("token_expires_at") or "")
        if expiry and expiry <= timezone.now():
            raise OAuthFailure("token_expired")
        if config.provider == "INSTAGRAM":
            if expiry and expiry < timezone.now()+timedelta(days=7):
                refreshed = meta_request("get", "https://graph.instagram.com/refresh_access_token",
                    params={"grant_type": "ig_refresh_token", "access_token": token})
                if not refreshed.get("access_token") or not refreshed.get("expires_in"):
                    raise OAuthFailure("token_expired")
                token = refreshed["access_token"]
                credentials["access_token"] = encrypt_string(token)
                updates["token_expires_at"] = (timezone.now()+timedelta(seconds=int(refreshed["expires_in"]))).isoformat()
            profile = meta_request("get", f"{base}/{account}", token, params={"fields": "user_id,username"})
            if not profile.get("username") or str(profile.get("user_id") or profile.get("id")) != account:
                raise OAuthFailure("no_instagram_account")
            # Verify current account/subscription access without the unsupported
            # permissions edge. Do not fabricate or overwrite recorded OAuth grants.
            updates.update(username=profile["username"])
            asset = account
        else:
            app_id, secret = app_credentials("WHATSAPP")
            debug = meta_request("get", f"{base}/debug_token", f"{app_id}|{secret}", params={"input_token": token}).get("data", {})
            if not debug.get("is_valid") or str(debug.get("app_id")) != app_id:
                raise OAuthFailure("token_expired")
            require_scopes(debug.get("scopes", []), "WHATSAPP")
            authorized = {str(target) for scope in debug.get("granular_scopes", [])
                if scope.get("scope") == "whatsapp_business_management" for target in scope.get("target_ids", [])}
            if str(config.metadata.get("waba_id")) not in authorized:
                raise OAuthFailure("permission_required")
            phone = meta_request("get", f"{base}/{account}", token, params={"fields": "id,display_phone_number,verified_name,status"})
            if str(phone.get("id")) != account or phone.get("status") != "CONNECTED":
                raise OAuthFailure("phone_registration_failed")
            asset = config.metadata.get("waba_id")
            if not asset:
                raise OAuthFailure("configuration_required")
            meta_request("get", f"{base}/{asset}", token, params={"fields": "id"})
            updates.update(display_phone_number=phone.get("display_phone_number"), verified_name=phone.get("verified_name"))
        subscriptions = meta_request("get", f"{base}/{asset}/subscribed_apps", token)
        app_id, _ = app_credentials(config.provider)
        apps = subscriptions.get("data", [])
        subscribed = any(str(row.get("id") or row.get("whatsapp_business_api_data", {}).get("id")) == app_id
            and (config.provider != "INSTAGRAM" or {"messages", "messaging_seen"}.issubset(row.get("subscribed_fields", []))) for row in apps)
        if not subscribed:
            raise OAuthFailure("webhook_subscription_failed")
        updates.update(last_verified_at=timezone.now().isoformat(), webhook_subscribed=True, error_code="", last_error="")
    except OAuthFailure as exc:
        updates.update(error_code=exc.code, last_error=ERRORS[exc.code])
        if exc.code == "webhook_subscription_failed":
            updates["webhook_subscribed"] = False
    except Exception:
        updates.update(error_code="meta_connection_failed", last_error=ERRORS["meta_connection_failed"])
    updates["last_checked_at"] = timezone.now().isoformat()
    with transaction.atomic():
        current = IntegrationConfig.objects.select_for_update().filter(pk=config_id, is_active=True).first()
        # A check started before disconnect/reconnect cannot overwrite the new credentials/status.
        if current and current.credentials == config.credentials:
            current.metadata = {**current.metadata, **updates}
            current.credentials = credentials
            current.save(update_fields=["metadata", "credentials", "updated_at"])
