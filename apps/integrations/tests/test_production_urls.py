"""Production URL contracts. Only synthetic credentials and mocked Meta HTTP."""
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.urls import resolve
from rest_framework.test import APIClient

from apps.integrations import connection_service as service
from apps.integrations.models import OAuthAttempt, IntegrationConfig
from apps.integrations.tests.test_connections import owner, client, ig_get, ig_post
from apps.integrations.views import InstagramWebhookView, WhatsAppWebhookView

ORIGIN = "https://studio.nextoracreations.co.in"
PATH = "/api/v1/integrations/oauth/instagram/callback/"
CALLBACK = ORIGIN + PATH
START = "/api/v1/integrations/oauth/instagram/login/"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def no_external_requests():
    with patch("requests.sessions.Session.request", side_effect=AssertionError("Live HTTP forbidden in URL tests")):
        yield


@pytest.fixture
def production(owner, settings):
    settings.DEBUG = False
    settings.META_REDIRECT_BASE_URL = ORIGIN
    settings.META_INSTAGRAM_REDIRECT_URI = ""
    settings.FRONTEND_URL = ORIGIN
    return owner


def callback():
    return service.callback_uri(RequestFactory().get("/", HTTP_HOST="ignored.example.test"), "INSTAGRAM")


def test_exact_production_callback_and_trailing_slash(production, settings):
    assert callback() == CALLBACK
    settings.META_REDIRECT_BASE_URL = ORIGIN + "/"
    assert callback() == CALLBACK
    settings.META_INSTAGRAM_REDIRECT_URI = CALLBACK
    settings.META_REDIRECT_BASE_URL = "https://unused.example.test"
    assert callback() == CALLBACK


@pytest.mark.parametrize("origin", [
    "http://studio.nextoracreations.co.in", "http://localhost:8002",
    "https://localhost", "https://127.0.0.1", "https://127.0.0.2", "https://[::1]",
    "https://LOCALHOST.", "https://demo.ngrok-free.app", "https://demo.ngrok-free.dev",
    "https://demo.ngrok.io", "https://demo.ngrok.app", "ftp://example.test",
])
@pytest.mark.parametrize("use_override", [True, False])
def test_unsafe_production_origins_rejected(production, settings, origin, use_override):
    if use_override:
        settings.META_INSTAGRAM_REDIRECT_URI = origin + PATH
    else:
        settings.META_REDIRECT_BASE_URL = origin
    with pytest.raises(service.OAuthFailure, match="configuration_required"):
        callback()


@pytest.mark.parametrize("uri", [
    CALLBACK.rstrip("/"), ORIGIN + "/api/v1/integrations/instagram/callback/",
    CALLBACK + "?extra=1", CALLBACK + "#fragment", CALLBACK + "?",
    " " + CALLBACK, "https://user:secret@example.test" + PATH,
    "https://example.test:bad" + PATH, "https://example.test:0" + PATH,
    "https://example.test\\@localhost" + PATH,
])
def test_noncanonical_override_rejected_without_rewriting(production, settings, uri):
    settings.META_INSTAGRAM_REDIRECT_URI = uri
    with pytest.raises(service.OAuthFailure, match="configuration_required"):
        callback()


def test_production_never_infers_request_host(production, settings):
    settings.META_REDIRECT_BASE_URL = ""
    with pytest.raises(service.OAuthFailure, match="configuration_required"):
        callback()
    response = client(production).get(START)
    assert response.status_code == 409
    assert response.data["code"] == "configuration_required"
    assert not OAuthAttempt.objects.exists()


@pytest.mark.parametrize("origin", ["http://localhost:8002", "http://127.0.0.1:8002", "https://demo.ngrok-free.app"])
def test_debug_supports_local_and_registered_tunnel(production, settings, origin):
    settings.DEBUG = True
    settings.META_REDIRECT_BASE_URL = origin
    assert callback() == origin + PATH


def test_debug_request_fallback_remains_local(production, settings):
    settings.DEBUG = True
    settings.META_REDIRECT_BASE_URL = ""
    settings.ALLOWED_HOSTS = ["localhost"]
    request = RequestFactory().get("/", HTTP_HOST="localhost:8002")
    assert service.callback_uri(request, "INSTAGRAM") == "http://localhost:8002" + PATH


def test_authorization_and_token_exchange_use_same_stored_uri(production, settings):
    result = client(production).get(START)
    assert result.status_code == 200
    url = urlparse(result.data["url"])
    assert (url.scheme, url.netloc, url.path) == ("https", "www.instagram.com", "/oauth/authorize")
    query = parse_qs(url.query)
    assert query["redirect_uri"] == [CALLBACK]
    attempt = OAuthAttempt.objects.get()
    assert attempt.redirect_uri == CALLBACK
    # A setting change during a flow must not change the code-exchange URI.
    settings.META_INSTAGRAM_REDIRECT_URI = "https://another.example.test" + PATH
    with patch("requests.get", side_effect=ig_get), patch("requests.post", side_effect=ig_post) as post:
        result = APIClient().get(PATH, {"code": "synthetic-code", "state": query["state"][0]})
    assert post.call_args_list[0].kwargs["data"]["redirect_uri"] == attempt.redirect_uri
    assert post.call_args_list[1].args[0].endswith("/subscribed_apps")
    assert result.url == ORIGIN + "/app/settings/channels?integration_success=instagram"
    assert IntegrationConfig.objects.get().is_active
    attempt.refresh_from_db()
    assert attempt.consumed_at is not None
    with patch("requests.post") as post:
        result = APIClient().get(PATH, {"code": "synthetic-code", "state": query["state"][0]})
    assert "error=invalid_state" in result.url
    post.assert_not_called()


def test_legacy_start_generates_canonical_callback(production):
    result = client(production).get("/api/v1/integrations/instagram/connect/")
    assert parse_qs(urlparse(result.data["url"]).query)["redirect_uri"] == [CALLBACK]
    assert resolve(PATH).func.view_class == resolve("/api/v1/integrations/instagram/callback/").func.view_class


@pytest.mark.parametrize("origin", ["http://localhost:5173", "https://demo.ngrok-free.app", "https://localhost", ""])
def test_unsafe_frontend_return_fails_closed(production, settings, origin):
    settings.FRONTEND_URL = origin
    assert client(production).get(START).status_code == 409
    assert APIClient().get(PATH).status_code == 409
    assert not OAuthAttempt.objects.exists()


@pytest.mark.parametrize("provider,view", [("instagram", InstagramWebhookView), ("whatsapp", WhatsAppWebhookView)])
def test_canonical_webhook_verification_and_signature_required(production, settings, provider, view):
    settings.META_VERIFY_TOKEN = "synthetic-webhook-verify-only"
    path = f"/api/v1/webhooks/meta/{provider}/"
    assert resolve(path).func.view_class == view
    c = APIClient()
    params = {"hub.mode": "subscribe", "hub.verify_token": settings.META_VERIFY_TOKEN, "hub.challenge": "synthetic-challenge"}
    response = c.get(path, params)
    assert response.status_code == 200 and response.content == b"synthetic-challenge"
    assert c.get(path, {**params, "hub.verify_token": "wrong"}).status_code == 403
    assert c.get(path, {**params, "hub.mode": "invalid"}).status_code == 403
    assert c.post(path, {}, format="json").status_code == 403


def test_whatsapp_embedded_signup_does_not_require_redirect(production, settings):
    settings.META_WHATSAPP_REDIRECT_URI = ""
    result = client(production).get("/api/v1/integrations/whatsapp/connect/")
    assert result.status_code == 200
    assert "config_id" in result.data and "url" not in result.data
    assert OAuthAttempt.objects.get().redirect_uri == ""
