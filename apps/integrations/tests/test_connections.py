"""Connection acceptance tests: external HTTP is mocked only in this test module."""
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch
import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.integrations.models import IntegrationConfig, OAuthAttempt
from apps.integrations import connection_service as service
from apps.integrations.health_service import verify_integration
from apps.conversations.outbound import configuration_status
from apps.core.utils.crypto import encrypt_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(settings):
    settings.META_APP_ID = "123456"
    settings.META_APP_SECRET = "test-secret"
    settings.META_INSTAGRAM_APP_ID = ""
    settings.META_INSTAGRAM_APP_SECRET = ""
    settings.META_REDIRECT_BASE_URL = "https://api.example.test"
    settings.META_INSTAGRAM_REDIRECT_URI = ""
    settings.FRONTEND_URL = "https://app.example.test"
    settings.META_WHATSAPP_CONFIG_ID = "54321"
    user = User.objects.create_user(email="connect@example.test", password="SafePass9!")
    org = Organization.objects.create(name="Connection test", slug="connection-test", owner=user)
    OrganizationMembership.objects.create(user=user, organization=org, role="OWNER")
    return user, org


def client(owner):
    c = APIClient()
    c.force_authenticate(owner[0])
    c.credentials(HTTP_X_ORGANIZATION_ID=str(owner[1].pk))
    return c


def response(body, status=200):
    return Mock(status_code=status, json=Mock(return_value=body))


def ig_start(owner):
    start = client(owner).get("/api/v1/integrations/instagram/connect/")
    assert start.status_code == 200
    return parse_qs(urlparse(start.data["url"]).query)["state"][0]


def ig_get(url, **kwargs):
    if url.endswith("/permissions"):
        return response({"error": {"code": 100}}, 400)
    if url.endswith("/access_token"):
        return response({"access_token": "long-token", "expires_in": 5184000})
    return response({"user_id": "90001", "username": "studio"})


def ig_post(url, **kwargs):
    return response({"access_token": "short-token", "user_id": "90001"} if url.endswith("access_token") else {"success": True})


def ig_callback(state, **extra):
    return APIClient().get("/api/v1/integrations/oauth/instagram/callback/", {"state": state, "code": "authorization-code", **extra})


def test_secure_state_and_configured_redirect(owner):
    one, two = ig_start(owner), ig_start(owner)
    assert one != two and len(one) >= 40
    attempt = OAuthAttempt.objects.latest("created_at")
    assert attempt.user == owner[0] and attempt.organization == owner[1]
    assert attempt.state_hash != two
    assert attempt.redirect_uri == "https://api.example.test/api/v1/integrations/oauth/instagram/callback/"
    assert not IntegrationConfig.objects.exists()


@pytest.mark.parametrize("case", ["invalid", "expired", "membership_removed", "wrong_provider"])
def test_invalid_state_never_exchanges(owner, case):
    state = ig_start(owner)
    if case == "invalid": state = "invalid"
    if case == "expired": OAuthAttempt.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    if case == "membership_removed": OrganizationMembership.objects.update(is_active=False)
    if case == "wrong_provider": OAuthAttempt.objects.update(provider="WHATSAPP")
    with patch("requests.post") as post:
        assert "error=invalid_state" in ig_callback(state).url
        post.assert_not_called()


def test_cancel_consumes_state(owner):
    state = ig_start(owner)
    assert "authorization_cancelled" in ig_callback(state, error="access_denied").url
    assert "invalid_state" in ig_callback(state).url


def test_instagram_verified_success_encrypted_single_use(owner):
    state = ig_start(owner)
    with patch("requests.get", side_effect=ig_get), patch("requests.post", side_effect=ig_post):
        result = ig_callback(state)
    assert "integration_success=instagram" in result.url
    assert "token" not in result.url and "code=" not in result.url
    config = IntegrationConfig.objects.get()
    assert config.connected_by == owner[0]
    assert config.credentials["access_token"] != "long-token"
    assert config.get_credential("access_token") == "long-token"
    assert configuration_status(config)[0] == "CONNECTED"
    assert "invalid_state" in ig_callback(state).url
    status = client(owner).get("/api/v1/integrations/status/")
    assert status.data["instagram"]["username"] == "studio"
    assert "long-token" not in str(status.data) and "credentials" not in str(status.data)


@pytest.mark.parametrize("failure", ["permission_required", "token_exchange_failed", "webhook_subscription_failed", "no_instagram_account"])
def test_instagram_failures_do_not_activate(owner, failure):
    def get(url, **kwargs):
        if failure == "permission_required" and url.endswith("/me"): return response({"error": {"code": 10}}, 400)
        if failure == "no_instagram_account" and url.endswith("/me"): return response({"id": "90001"})
        return ig_get(url, **kwargs)
    def post(url, **kwargs):
        if failure == "token_exchange_failed" and url.endswith("access_token"): return response({"error": {}}, 400)
        if failure == "webhook_subscription_failed" and url.endswith("subscribed_apps"): return response({"success": False})
        return ig_post(url, **kwargs)
    state = ig_start(owner)
    with patch("requests.get", side_effect=get), patch("requests.post", side_effect=post):
        assert f"error={failure}" in ig_callback(state).url
    assert not IntegrationConfig.objects.exists()


def wa_get(url, **kwargs):
    if url.endswith("oauth/access_token"): return response({"access_token": "wa-token"})
    if url.endswith("debug_token"):
        return response({"data": {"is_valid": True, "app_id": "123456", "scopes": service.SCOPES["WHATSAPP"],
            "granular_scopes": [{"scope": "whatsapp_business_management", "target_ids": ["888"]}]}})
    if url.endswith("phone_numbers"):
        return response({"data": [{"id": "90002", "display_phone_number": "+919876543210", "verified_name": "Studio", "status": "PENDING"}]})
    return response({"id": "888", "name": "Studio", "owner_business_info": {"id": "777"}})


def wa_start(owner):
    result = client(owner).get("/api/v1/integrations/whatsapp/connect/")
    assert result.status_code == 200
    assert result.data["config_id"] == "54321" and "url" not in result.data
    assert "secret" not in str(result.data)
    return result.data["state"]


def wa_complete(owner, state, **extra):
    return client(owner).post("/api/v1/integrations/whatsapp/complete/", {
        "state": state, "code": "wa-code", "waba_id": "888", "phone_number_id": "90002", **extra}, format="json")


def test_whatsapp_embedded_signup_verifies_registers_and_subscribes(owner):
    state = wa_start(owner)
    with patch("requests.get", side_effect=wa_get), patch("requests.post", return_value=response({"success": True})) as post:
        result = wa_complete(owner, state)
    assert result.status_code == 200 and result.data["status"] == "connected"
    assert post.call_args_list[0].args[0].endswith("/90002/register")
    assert post.call_args_list[1].args[0].endswith("/888/subscribed_apps")
    config = IntegrationConfig.objects.get()
    assert config.get_credential("access_token") == "wa-token"
    assert len(config.get_credential("registration_pin")) == 6
    assert config.metadata["business_id"] == "777"
    assert configuration_status(config)[0] == "CONNECTED"
    assert wa_complete(owner, state).data["code"] == "invalid_state"


@pytest.mark.parametrize("change", [{"waba_id": "999"}, {"phone_number_id": "111"}])
def test_client_asset_ids_are_verified_with_meta(owner, change):
    state = wa_start(owner)
    with patch("requests.get", side_effect=wa_get), patch("requests.post") as post:
        assert wa_complete(owner, state, **change).data["code"] == "asset_not_authorized"
        post.assert_not_called()
    assert not IntegrationConfig.objects.exists()


def test_completion_bound_to_initiating_user(owner):
    state = wa_start(owner)
    other = User.objects.create_user(email="otheradmin@example.test")
    OrganizationMembership.objects.create(user=other, organization=owner[1], role="ADMIN")
    with patch("requests.get") as get:
        assert wa_complete((other, owner[1]), state).data["code"] == "invalid_state"
        get.assert_not_called()


def test_whatsapp_failed_subscription_does_not_activate(owner):
    state = wa_start(owner)
    with patch("requests.get", side_effect=wa_get), patch("requests.post", side_effect=[response({"success": True}), response({"success": False})]):
        assert wa_complete(owner, state).data["code"] == "webhook_subscription_failed"
    assert not IntegrationConfig.objects.exists()


def test_duplicate_destination_blocked_before_subscription(owner):
    other = Organization.objects.create(name="Other", slug="other", owner=owner[0])
    IntegrationConfig.objects.create(organization=other, provider="INSTAGRAM", metadata={"destination_id": "90001"})
    state = ig_start(owner)
    with patch("requests.get", side_effect=ig_get), patch("requests.post", side_effect=ig_post) as post:
        assert "account_already_connected_to_another_workspace" in ig_callback(state).url
        assert post.call_count == 1
    with pytest.raises(IntegrityError), transaction.atomic():
        IntegrationConfig.objects.create(organization=owner[1], provider="INSTAGRAM", metadata={"destination_id": "90001"})


def connected(owner, provider="INSTAGRAM"):
    return IntegrationConfig.objects.create(organization=owner[1], provider=provider,
        credentials={"access_token": encrypt_string("existing-token")}, metadata={"destination_id": "90001", "account_id": "90001",
        "waba_id": "888", "webhook_subscribed": True, "last_verified_at": timezone.now().isoformat()})


def test_health_detects_revoked_token(owner):
    config = connected(owner)
    with patch("requests.get", return_value=response({"error": {"code": 190}}, 400)):
        verify_integration(config.pk)
    config.refresh_from_db()
    assert configuration_status(config)[0] == "TOKEN_EXPIRED"


def test_health_subscription_and_permissions(owner):
    config = connected(owner)
    def get(url, **kwargs):
        if url.endswith("subscribed_apps"): return response({"data": [{"id": "123456", "subscribed_fields": ["messages", "messaging_seen"]}]})
        return ig_get(url, **kwargs)
    with patch("requests.get", side_effect=get): verify_integration(config.pk)
    config.refresh_from_db()
    assert configuration_status(config)[0] == "CONNECTED"
    with patch("requests.get", side_effect=lambda url, **kw: response({"data": []}) if url.endswith("subscribed_apps") else ig_get(url, **kw)):
        verify_integration(config.pk)
    config.refresh_from_db()
    assert configuration_status(config)[0] == "CONFIGURATION_REQUIRED"


def test_disconnect_removes_credentials_and_preserves_mapping(owner):
    config = connected(owner)
    with patch("requests.delete", return_value=response({"success": True})) as delete:
        assert client(owner).post("/api/v1/integrations/instagram/disconnect/").status_code == 200
        delete.assert_called_once()
    config.refresh_from_db()
    assert not config.is_active and not config.credentials
    assert config.metadata["destination_id"] == "90001"
    assert configuration_status(config)[0] == "DISCONNECTED"


def test_non_admin_cannot_connect_or_disconnect(owner):
    OrganizationMembership.objects.update(role="MEMBER")
    assert client(owner).get("/api/v1/integrations/instagram/connect/").status_code == 403
    assert client(owner).post("/api/v1/integrations/whatsapp/disconnect/").status_code == 403


def test_missing_meta_config_is_actionable(owner, settings):
    settings.META_WHATSAPP_CONFIG_ID = ""
    result = client(owner).get("/api/v1/integrations/whatsapp/connect/")
    assert result.status_code == 409 and "configuration ID" in result.data["detail"]


@pytest.mark.parametrize("body,expected", [({"error": {"code": 190}}, "token_expired"), ({"error": {"code": 10}}, "permission_required"), ({"error": {"code": 4}}, "rate_limited")])
def test_meta_failure_is_safe_and_actionable(owner, body, expected):
    state = wa_start(owner)
    with patch("requests.get", return_value=response(body, 400)):
        result = wa_complete(owner, state)
    assert result.data["code"] == expected
    assert "wa-code" not in str(result.data) and "test-secret" not in str(result.data)


def test_timeout_does_not_activate(owner):
    import requests
    state = wa_start(owner)
    with patch("requests.get", side_effect=requests.Timeout("url?client_secret=private")):
        result = wa_complete(owner, state)
    assert result.status_code == 409
    assert "private" not in str(result.data)
    assert not IntegrationConfig.objects.exists()


def test_health_does_not_resurrect_disconnected_channel(owner):
    config = connected(owner)
    def get(url, **kwargs):
        IntegrationConfig.objects.filter(pk=config.pk).update(is_active=False, credentials={})
        return response({"error": {"code": 190}}, 400)
    with patch("requests.get", side_effect=get): verify_integration(config.pk)
    config.refresh_from_db()
    assert not config.is_active and config.credentials == {}


def test_instagram_refresh_before_expiry(owner):
    config = connected(owner)
    config.metadata["token_expires_at"] = (timezone.now()+timedelta(days=3)).isoformat()
    config.save()
    def get(url, **kwargs):
        if url.endswith("refresh_access_token"): return response({"access_token": "refreshed-token", "expires_in": 5184000})
        if url.endswith("subscribed_apps"): return response({"data": [{"id": "123456", "subscribed_fields": ["messages", "messaging_seen"]}]})
        return ig_get(url, **kwargs)
    with patch("requests.get", side_effect=get): verify_integration(config.pk)
    config.refresh_from_db()
    assert config.get_credential("access_token") == "refreshed-token"
    assert configuration_status(config)[0] == "CONNECTED"


def test_log_filter_removes_oauth_query_secrets():
    import logging
    from apps.core.logging import CorrelationIdFilter
    record = logging.LogRecord("django.server", logging.INFO, "", 0, 'GET /callback/?code=%s&state=%s', ('private-code', 'private-state'), None)
    CorrelationIdFilter().filter(record)
    assert "private-code" not in record.getMessage() and "private-state" not in record.getMessage()


@pytest.mark.parametrize("message_type,content,expected", [("location", {"name": "Studio", "latitude": 12.9, "longitude": 80.2}, "Studio"), ("contacts", [{"name": {"formatted_name": "Customer"}}], "Customer")])
def test_whatsapp_location_and_contact_messages(message_type, content, expected):
    from apps.integrations.meta.whatsapp.parser import WhatsAppInboundParser
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "90002"}, "messages": [{"id": "msg-1", "from": "919123456789", "type": message_type, message_type: content}]}}]}]}
    messages = WhatsAppInboundParser().parse_messages(payload)
    assert len(messages) == 1 and messages[0].text == expected
    assert messages[0].attachments[0]["raw"] == content


def test_whatsapp_missing_permissions_does_not_register(owner):
    state = wa_start(owner)
    def get(url, **kwargs):
        if url.endswith("debug_token"): return response({"data": {"is_valid": True, "app_id": "123456", "scopes": []}})
        return wa_get(url, **kwargs)
    with patch("requests.get", side_effect=get), patch("requests.post") as post:
        assert wa_complete(owner, state).data["code"] == "permission_required"
        post.assert_not_called()


def test_whatsapp_health_detects_lost_messaging_permission(owner):
    config = connected(owner, "WHATSAPP")
    with patch("requests.get", return_value=response({"data": {"is_valid": True, "app_id": "123456", "scopes": ["whatsapp_business_management"]}})):
        verify_integration(config.pk)
    config.refresh_from_db()
    assert configuration_status(config)[0] == "PERMISSION_REQUIRED"
