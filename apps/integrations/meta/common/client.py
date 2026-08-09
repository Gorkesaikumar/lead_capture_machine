"""
HTTP Client for Meta Graph API communication.
Handles requests with configurable API version, connection pooling, safe retries,
timeouts, and strict token sanitization/masking.
"""
import logging
from typing import Any, Dict, Optional
from django.conf import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from apps.integrations.meta.common.exceptions import ProviderSendError

logger = logging.getLogger("apps.integrations.meta")


def mask_token(token: Optional[str]) -> str:
    """Masks sensitive access token for safe diagnostic logging."""
    if not token or len(token) < 8:
        return "[EMPTY/SHORT]"
    return f"{token[:4]}...{token[-4:]}"


class MetaGraphClient:
    """
    Robust client for dispatching requests to Meta Graph API.
    Configurable API version, timeouts, structured error handling, and safe retries.
    """

    DEFAULT_API_VERSION = "v21.0"
    DEFAULT_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        access_token: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
    ):
        self._access_token = access_token
        self.api_version = (
            api_version
            or getattr(settings, "META_GRAPH_API_VERSION", self.DEFAULT_API_VERSION)
        )
        self.timeout = timeout or getattr(
            settings, "META_HTTP_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT_SECONDS
        )
        self.session = self._create_retry_session(max_retries=max_retries)

    @classmethod
    def _create_retry_session(cls, max_retries: int = 3) -> requests.Session:
        """
        Builds a requests session configured with exponential backoff retries for transient 5xx errors.
        """
        session = requests.Session()
        if max_retries > 0:
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST", "GET"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        return session

    @property
    def access_token(self) -> str:
        return self._access_token or ""

    @property
    def base_url(self) -> str:
        token = self.access_token
        if token and (token.startswith("IG") or token.startswith("EAAG")):
            # Instagram User Access Tokens (IGAA...) route to graph.instagram.com
            if token.startswith("IG"):
                return f"https://graph.instagram.com/{self.api_version}"
        return f"https://graph.facebook.com/{self.api_version}"

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a GET request to Meta Graph API.
        """
        token = access_token or self.access_token
        if not token:
            logger.error("Meta Graph API Access Token is not configured.")
            raise ProviderSendError("Access token is missing.")

        clean_endpoint = endpoint.lstrip("/")
        url = f"{self.base_url}/{clean_endpoint}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = self.session.get(
                url=url,
                params=params or {},
                headers=headers,
                timeout=self.timeout,
            )
            response_json = response.json() if response.content else {}
        except requests.exceptions.Timeout as exc:
            logger.error("Meta Graph API timeout (%ss) on GET %s", self.timeout, endpoint)
            raise ProviderSendError(f"Request timeout calling Meta API: {str(exc)}") from exc
        except requests.RequestException as exc:
            logger.error("Meta Graph API network error on GET %s: %s", endpoint, str(exc))
            raise ProviderSendError(f"Network error calling Meta API: {str(exc)}") from exc
        except ValueError as exc:
            logger.error("Meta Graph API non-JSON response on GET %s: HTTP %s", endpoint, response.status_code)
            raise ProviderSendError("Invalid JSON response from Meta API.") from exc

        if not response.ok:
            error_data = response_json.get("error", {})
            error_message = error_data.get("message", f"HTTP {response.status_code}")
            error_code = error_data.get("code")
            error_subcode = error_data.get("error_subcode")
            logger.warning(
                "Meta Graph API GET error: HTTP %s [code=%s, subcode=%s] - %s",
                response.status_code,
                error_code,
                error_subcode,
                error_message,
            )
            raise ProviderSendError(f"Meta API error ({error_code}): {error_message}")

        return response_json

    def post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a POST request to Meta Graph API.

        Args:
            endpoint: Relative path (e.g. 'me/messages')
            payload: JSON body payload
            access_token: Optional token override

        Returns:
            Dict[str, Any]: Parsed JSON response.

        Raises:
            ProviderSendError: If the request fails, times out, or Meta returns an error.
        """
        token = access_token or self.access_token
        if not token:
            logger.error("Meta Graph API Access Token is not configured.")
            raise ProviderSendError("Access token is missing.")

        clean_endpoint = endpoint.lstrip("/")
        url = f"{self.base_url}/{clean_endpoint}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "Calling Meta Graph API: POST %s [token=%s]",
            url,
            mask_token(token),
        )

        try:
            response = self.session.post(
                url=url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response_json = response.json() if response.content else {}
        except requests.exceptions.Timeout as exc:
            logger.error("Meta Graph API timeout (%ss) on endpoint %s", self.timeout, endpoint)
            raise ProviderSendError(f"Request timeout calling Meta API: {str(exc)}") from exc
        except requests.RequestException as exc:
            logger.error("Meta Graph API network error on endpoint %s: %s", endpoint, str(exc))
            raise ProviderSendError(f"Network error calling Meta API: {str(exc)}") from exc
        except ValueError as exc:
            logger.error("Meta Graph API non-JSON response on endpoint %s: HTTP %s", endpoint, response.status_code)
            raise ProviderSendError("Invalid JSON response from Meta API.") from exc

        if not response.ok:
            error_data = response_json.get("error", {})
            error_message = error_data.get("message", f"HTTP {response.status_code}")
            error_code = error_data.get("code")
            error_subcode = error_data.get("error_subcode")
            logger.error(
                "Meta Graph API error response: HTTP %s [code=%s, subcode=%s] - %s",
                response.status_code,
                error_code,
                error_subcode,
                error_message,
            )
            raise ProviderSendError(
                f"Meta API error ({error_code}): {error_message}",
                code=error_code,
                subcode=error_subcode,
                raw_error=error_data,
            )

        return response_json
