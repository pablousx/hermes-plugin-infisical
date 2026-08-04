"""Infisical SecretSource for Hermes Agent.

The source is read-only and startup-scoped. It authenticates with Universal
Auth, fetches one project/environment/path, and returns environment-shaped
secrets to Hermes. The Hermes orchestrator owns precedence and environment
writes; this module never persists downloaded values.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from agent.secret_sources.base import ErrorKind, FetchResult, SecretSource, is_valid_env_name

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_USER_AGENT = "hermes-plugin-infisical/0.1.0"
class InfisicalClientError(RuntimeError):
    """Sanitized failure carrying a Hermes error kind.

    Messages must never include response bodies, credentials, access tokens,
    or secret values.
    """

    def __init__(self, kind: ErrorKind, message: str, *, status: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


@dataclass(frozen=True)
class SourceConfig:
    project_id: str
    environment: str
    secret_path: str
    recursive: bool
    allow_insecure_http: bool


def _normalize_path(raw: object) -> str:
    value = str(raw or "/").strip() or "/"
    if not value.startswith("/"):
        value = "/" + value
    if value != "/":
        value = value.rstrip("/")
    return value


def _parse_config(cfg: Mapping[str, object]) -> SourceConfig:
    project_id = cfg.get("project_id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("secrets.infisical.project_id is required")

    environment = cfg.get("environment", "prod")
    if not isinstance(environment, str) or not environment.strip():
        raise ValueError("secrets.infisical.environment must be a non-empty string")

    recursive = cfg.get("recursive", False)
    if not isinstance(recursive, bool):
        raise ValueError("secrets.infisical.recursive must be true or false")

    allow_insecure = cfg.get("allow_insecure_http", False)
    if not isinstance(allow_insecure, bool):
        raise ValueError("secrets.infisical.allow_insecure_http must be true or false")

    return SourceConfig(
        project_id=project_id.strip(),
        environment=environment.strip(),
        secret_path=_normalize_path(cfg.get("secret_path", "/")),
        recursive=recursive,
        allow_insecure_http=allow_insecure,
    )


def _error_kind_for_status(status: int) -> ErrorKind:
    if status in (401, 403):
        return ErrorKind.AUTH_FAILED
    if status == 404:
        return ErrorKind.REF_INVALID
    if status in (408, 429) or status >= 500:
        return ErrorKind.NETWORK
    return ErrorKind.INTERNAL


class _SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that could forward Authorization to another origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(newurl)
        if _origin(old) != _origin(new):
            raise InfisicalClientError(
                ErrorKind.NETWORK, "Infisical redirected to a different origin"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _origin(parsed: urllib.parse.SplitResult) -> tuple[str, str | None, int | None]:
    """Return a normalized URL origin, including implicit default ports."""
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), parsed.hostname, parsed.port or default_port


class InfisicalClient:
    """Small, dependency-free client for the two Infisical endpoints we need."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        allow_insecure_http: bool = False,
    ):
        self.base_url = self._validate_base_url(base_url, allow_insecure_http)
        self.timeout = float(timeout) if float(timeout) > 0 else _DEFAULT_TIMEOUT
        self.max_response_bytes = max(1, int(max_response_bytes))
        self._opener = urllib.request.build_opener(_SameOriginRedirectHandler())

    @staticmethod
    def _validate_base_url(base_url: str, allow_insecure_http: bool) -> str:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("INFISICAL_HOST_URL is required")
        normalized = base_url.strip().rstrip("/")
        parsed = urllib.parse.urlsplit(normalized)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("INFISICAL_HOST_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("INFISICAL_HOST_URL must not contain credentials, query, or fragment")
        if parsed.scheme == "http" and not allow_insecure_http:
            raise ValueError(
                "INFISICAL_HOST_URL must use HTTPS; set allow_insecure_http only "
                "for a trusted private network"
            )
        return normalized

    def _request_json(self, request: urllib.request.Request) -> dict:
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            kind = _error_kind_for_status(exc.code)
            raise InfisicalClientError(
                kind, f"Infisical request failed with HTTP {exc.code}", status=exc.code
            ) from None
        except InfisicalClientError:
            raise
        except (urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError):
            raise InfisicalClientError(
                ErrorKind.NETWORK, "Infisical network request failed"
            ) from None

        if len(raw) > self.max_response_bytes:
            raise InfisicalClientError(
                ErrorKind.INTERNAL, "Infisical response exceeded the configured size limit"
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise InfisicalClientError(
                ErrorKind.INTERNAL, "Infisical returned an invalid JSON response"
            ) from None
        if not isinstance(payload, dict):
            raise InfisicalClientError(
                ErrorKind.INTERNAL, "Infisical returned an unexpected response shape"
            )
        return payload

    def login(self, client_id: str, client_secret: str) -> str:
        body = json.dumps({"clientId": client_id, "clientSecret": client_secret}).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310 -- base URL is validated
            f"{self.base_url}/api/v1/auth/universal-auth/login",
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
            method="POST",
        )
        payload = self._request_json(request)
        token = payload.get("accessToken")
        if not isinstance(token, str) or not token.strip():
            raise InfisicalClientError(
                ErrorKind.AUTH_FAILED, "Infisical authentication returned no access token"
            )
        return token.strip()

    def list_secrets(
        self,
        access_token: str,
        project_id: str,
        environment: str,
        secret_path: str,
        recursive: bool,
    ) -> tuple[dict[str, str], list[str]]:
        query = urllib.parse.urlencode(
            {
                "workspaceId": project_id,
                "environment": environment,
                "secretPath": secret_path,
                "recursive": str(recursive).lower(),
            }
        )
        request = urllib.request.Request(  # noqa: S310 -- base URL is validated
            f"{self.base_url}/api/v3/secrets/raw?{query}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="GET",
        )
        payload = self._request_json(request)
        entries = payload.get("secrets")
        if not isinstance(entries, list):
            raise InfisicalClientError(
                ErrorKind.INTERNAL, "Infisical response did not contain a secrets list"
            )

        secrets: dict[str, str] = {}
        warnings: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                warnings.append("skipped a malformed Infisical secret entry")
                continue
            key = entry.get("secretKey")
            value = entry.get("secretValue")
            if not isinstance(key, str) or not is_valid_env_name(key):
                warnings.append("skipped an Infisical secret with an invalid environment name")
                continue
            if not isinstance(value, str):
                warnings.append(f"skipped {key}: value was not a string")
                continue
            if value == "":
                warnings.append(f"skipped {key}: value was empty")
                continue
            if key in secrets:
                warnings.append(f"skipped duplicate Infisical secret {key}; first value won")
                continue
            secrets[key] = value
        return secrets, warnings


class InfisicalSource(SecretSource):
    """Hermes read-only bulk source backed by one Infisical project/path."""

    name = "infisical"
    label = "Infisical"
    shape = "bulk"
    scheme = None

    BOOTSTRAP_ENV_VARS = (
        "INFISICAL_HOST_URL",
        "INFISICAL_UNIVERSAL_AUTH_CLIENT_ID",
        "INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET",
    )

    def __init__(self, client_factory: Callable[..., InfisicalClient] | None = None):
        self._client_factory = client_factory or InfisicalClient

    def override_existing(self, cfg: dict) -> bool:
        if not isinstance(cfg, dict):
            return False
        if "override_existing" not in cfg:
            return True
        value = cfg.get("override_existing")
        return value if isinstance(value, bool) else False

    def protected_env_vars(self, cfg: dict):
        return frozenset(self.BOOTSTRAP_ENV_VARS)

    def config_schema(self) -> dict:
        return {
            "project_id": {"description": "Infisical project/workspace ID", "default": ""},
            "environment": {"description": "Infisical environment slug", "default": "prod"},
            "secret_path": {"description": "Folder path to load", "default": "/"},
            "recursive": {"description": "Load child folders recursively", "default": False},
            "override_existing": {
                "description": "Replace matching .env/shell values",
                "default": True,
            },
            "allow_insecure_http": {
                "description": "Allow HTTP for trusted private networks",
                "default": False,
            },
        }

    def remediation(self, kind: ErrorKind | None, cfg: dict) -> str:
        if kind == ErrorKind.NOT_CONFIGURED:
            return "Set the Infisical bootstrap environment and secrets.infisical.project_id."
        if kind in (ErrorKind.AUTH_FAILED, ErrorKind.AUTH_EXPIRED):
            return "Rotate or re-authorize the Infisical Universal Auth Machine Identity."
        if kind == ErrorKind.REF_INVALID:
            return "Verify the Infisical project_id, environment, and secret_path."
        if kind in (ErrorKind.NETWORK, ErrorKind.TIMEOUT):
            return "Verify INFISICAL_HOST_URL, TLS, DNS, and network reachability."
        return "Check the Hermes gateway log for the sanitized Infisical error."

    def fetch(self, cfg: dict, home_path: Path) -> FetchResult:
        result = FetchResult()
        if not self.is_enabled(cfg):
            return result

        try:
            source_cfg = _parse_config(cfg if isinstance(cfg, dict) else {})
            bootstrap = {name: os.environ.get(name, "").strip() for name in self.BOOTSTRAP_ENV_VARS}
            missing = [name for name, value in bootstrap.items() if not value]
            if missing:
                result.error = (
                    "Infisical bootstrap environment is incomplete: " + ", ".join(missing)
                )
                result.error_kind = ErrorKind.NOT_CONFIGURED
                return result

            client = self._client_factory(
                base_url=bootstrap["INFISICAL_HOST_URL"],
                timeout=self.fetch_timeout_seconds(cfg),
                allow_insecure_http=source_cfg.allow_insecure_http,
            )
            token = client.login(
                bootstrap["INFISICAL_UNIVERSAL_AUTH_CLIENT_ID"],
                bootstrap["INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET"],
            )
            secrets, warnings = client.list_secrets(
                token,
                source_cfg.project_id,
                source_cfg.environment,
                source_cfg.secret_path,
                source_cfg.recursive,
            )
            result.secrets = secrets
            result.warnings.extend(warnings)
            if not secrets:
                result.warnings.append(
                    "Infisical returned no usable secrets for the configured path"
                )
            return result
        except ValueError as exc:
            result.error = str(exc)
            result.error_kind = ErrorKind.NOT_CONFIGURED
            return result
        except InfisicalClientError as exc:
            result.error = str(exc)
            result.error_kind = exc.kind
            return result
        except Exception:
            result.error = "Infisical secret source failed internally"
            result.error_kind = ErrorKind.INTERNAL
            return result


__all__ = [
    "InfisicalClient",
    "InfisicalClientError",
    "InfisicalSource",
    "SourceConfig",
]
