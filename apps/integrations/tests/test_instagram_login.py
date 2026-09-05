"""Instagram Login contracts; no live provider calls or real credentials."""
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import pytest
import requests
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.integrations import connection_service as service
from apps.integrations.health_service import verify_integration
from apps.integrations.models import IntegrationConfig
from apps.integrations.tests.test_connections import (
    owner, client, ig_start, ig_callback, ig_get, ig_post, response, connected,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def no_live_http():
    with patch("requests.sessions.Session.request", side_effect=AssertionError("Live HTTP forbidden")):
        yield


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("grant_format", ["missing", "string", "list"])
def test_instagram_login_full_sequence(owner, wrapped, grant_format):
    grants = service.SCOPES["INSTAGRAM"]
    payload = {"access_token": "short-token", "user_id": "90001"}
    if grant_format != "missing":
        payload["permissions"] = ",".join(grants) if grant_format == "string" else grants
    start = client(owner).get("/api/v1/integrations/oauth/instagram/login/")
    query = parse_qs(urlparse(start.data["url"]).query)
    assert query["scope"] == [",".join(grants)]
    calls = []

    def post(url, **kwargs):
        calls.append(("post", url, kwargs))
        if url.endswith("oauth/access_token"):
            return response({"data": [payload]} if wrapped else payload)
        return ig_post(url, **kwargs)

    def get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return ig_get(url, **kwargs)

    with patch("requests.get", side_effect=get), patch("requests.post", side_effect=post):
        result = ig_callback(query["state"][0])
    assert "integration_success=instagram" in result.url
    base = service.graph_base("INSTAGRAM")
    assert [(method, url) for method, url, _ in calls] == [
        ("post", "https://api.instagram.com/oauth/access_token"),
        ("get", "https://graph.instagram.com/access_token"),
        ("get", f"{base}/90001"),
        ("post", f"{base}/90001/subscribed_apps"),
    ]
    assert calls[0][2]["data"]["redirect_uri"] == query["redirect_uri"][0]
    assert calls[1][2]["params"] == {
        "grant_type": "ig_exchange_token", "client_secret": "test-secret", "access_token": "short-token",
    }
    for _, _, kwargs in calls[2:]:
        assert kwargs["headers"]["Authorization"] == "Bearer long-token"
    assert "user_id" in calls[2][2]["params"]["fields"].split(",")
    assert "username" in calls[2][2]["params"]["fields"].split(",")
    assert calls[3][2]["data"]["subscribed_fields"] == "messages,messaging_seen"
    config = IntegrationConfig.objects.get()
    assert config.organization == owner[1] and config.connected_by == owner[0]
    assert config.get_credential("access_token") == "long-token"
    assert "long-token" not in json.dumps(config.credentials)
    assert parse_datetime(config.metadata["token_expires_at"]) > timezone.now()
    assert config.metadata["requested_scopes"] == grants
    assert config.metadata["scopes"] == ([] if grant_format == "missing" else grants)
    assert config.metadata["scopes_source"] == ("not_returned" if grant_format == "missing" else "token_response")


@pytest.mark.parametrize("grants", [[], "", "instagram_business_basic", ["instagram_business_manage_messages"], None, {}, [False]])
def test_explicit_missing_or_malformed_grants_stop_before_exchange(owner, grants):
    state = ig_start(owner)
    with patch("requests.post", return_value=response({"access_token": "short-token", "user_id": "90001", "permissions": grants})), patch("requests.get") as get:
        assert "error=permission_required" in ig_callback(state).url
    get.assert_not_called()
    assert not IntegrationConfig.objects.exists()


@pytest.mark.parametrize("profile", [{}, {"user_id": "90001"}, {"username": "studio"}, {"user_id": "other", "username": "studio"}, {"user_id": "90001", "username": " "}, {"user_id": "90001", "username": []}])
def test_missing_or_wrong_instagram_profile_never_subscribes(owner, profile):
    state = ig_start(owner)
    def get(url, **kwargs):
        return response(profile) if url.endswith("/90001") else ig_get(url, **kwargs)
    with patch("requests.get", side_effect=get), patch("requests.post", side_effect=ig_post) as post:
        assert "error=no_instagram_account" in ig_callback(state).url
    assert post.call_count == 1
    assert not IntegrationConfig.objects.exists()


@pytest.mark.parametrize("account", [None, "", "not-an-id", "../permissions", {}, 0])
def test_invalid_account_from_code_exchange_stops_before_graph(owner, account):
    state = ig_start(owner)
    with patch("requests.post", return_value=response({"access_token": "short-token", "user_id": account})), patch("requests.get") as get:
        assert "error=no_instagram_account" in ig_callback(state).url
    get.assert_not_called()
    assert not IntegrationConfig.objects.exists()


@pytest.mark.parametrize("payload", [{}, {"access_token": "", "expires_in": 5184000}, {"access_token": [], "expires_in": 5184000}, {"access_token": "long-token"}, *[{"access_token": "long-token", "expires_in": expiry} for expiry in [0, -1, "invalid", True, 1.5, 10**30]]])
def test_invalid_long_lived_response_does_not_activate(owner, payload):
    state = ig_start(owner)
    with patch("requests.get", return_value=response(payload)), patch("requests.post", side_effect=ig_post):
        assert "error=token_exchange_failed" in ig_callback(state).url
    assert not IntegrationConfig.objects.exists()


@pytest.mark.parametrize("stage", ["short", "long", "profile", "subscription"])
@pytest.mark.parametrize("code,expected", [(10, "permission_required"), (200, "permission_required"), (190, "token_expired"), (100, None)])
def test_provider_failures_remain_safe_and_do_not_activate(owner, stage, code, expected, caplog):
    state = ig_start(owner)
    failure = response({"error": {"code": code, "message": "PRIVATE-PROVIDER-BODY short-token long-token test-secret authorization-code"}}, 400)
    def get(url, **kwargs):
        if (stage == "long" and url.endswith("/access_token")) or (stage == "profile" and url.endswith("/90001")):
            return failure
        return ig_get(url, **kwargs)
    def post(url, **kwargs):
        if (stage == "short" and url.endswith("/access_token")) or (stage == "subscription" and url.endswith("/subscribed_apps")):
            return failure
        return ig_post(url, **kwargs)
    expected = expected or {"short": "token_exchange_failed", "long": "token_exchange_failed", "profile": "no_instagram_account", "subscription": "webhook_subscription_failed"}[stage]
    with patch("requests.get", side_effect=get), patch("requests.post", side_effect=post):
        result = ig_callback(state)
    assert f"error={expected}" in result.url
    assert not IntegrationConfig.objects.exists()
    output = caplog.text + result.url
    for secret in ["PRIVATE-PROVIDER-BODY", "short-token", "long-token", "test-secret", "authorization-code"]:
        assert secret not in output


def test_network_exception_url_never_logged(owner, caplog):
    state = ig_start(owner)
    with patch("requests.post", side_effect=ig_post), patch("requests.get", side_effect=requests.RequestException("https://graph.instagram.com/access_token?access_token=PRIVATE-TOKEN&client_secret=PRIVATE-SECRET")):
        result = ig_callback(state)
    assert "error=token_exchange_failed" in result.url
    assert "PRIVATE-TOKEN" not in caplog.text and "PRIVATE-SECRET" not in caplog.text
    assert not IntegrationConfig.objects.exists()


def test_health_uses_profile_and_subscription_without_rewriting_grants(owner):
    config = connected(owner)
    config.metadata["scopes"] = ["instagram_business_basic", "instagram_business_manage_messages"]
    config.metadata["scopes_source"] = "token_response"
    config.save()
    def get(url, **kwargs):
        if url.endswith("/subscribed_apps"):
            return response({"data": [{"id": "123456", "subscribed_fields": ["messages", "messaging_seen"]}]})
        return ig_get(url, **kwargs)
    with patch("requests.get", side_effect=get) as get_mock:
        verify_integration(config.pk)
    assert all(not call.args[0].endswith("/permissions") for call in get_mock.call_args_list)
    assert get_mock.call_count == 2
    config.refresh_from_db()
    assert config.metadata["error_code"] == ""
    assert config.metadata["scopes"] == service.SCOPES["INSTAGRAM"]
    assert config.metadata["scopes_source"] == "token_response"


@pytest.mark.parametrize("stage", ["profile", "subscription"])
def test_health_preserves_permission_denied_behavior(owner, stage):
    config = connected(owner)
    def get(url, **kwargs):
        if stage == "profile" or url.endswith("/subscribed_apps"):
            return response({"error": {"code": 10}}, 400)
        return ig_get(url, **kwargs)
    with patch("requests.get", side_effect=get):
        verify_integration(config.pk)
    config.refresh_from_db()
    assert config.metadata["error_code"] == "permission_required"
