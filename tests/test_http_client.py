from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest
from agent.secret_sources.base import ErrorKind

from infisical_source import InfisicalClient, InfisicalClientError


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._data = json.dumps(payload).encode()
        self.status = status

    def read(self, size: int = -1) -> bytes:
        return self._data[:size] if size >= 0 else self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_login_and_list_secrets(monkeypatch):
    calls = []
    responses = iter([
        FakeResponse({"accessToken": "access-value", "expiresIn": 7200}),
        FakeResponse({"secrets": [
            {"secretKey": "ALPHA_API_KEY", "secretValue": "alpha-value"},
            {"secretKey": "BETA_TOKEN", "secretValue": "beta-value"},
        ], "imports": []}),
    ])

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return next(responses)

    client = InfisicalClient("https://infisical.example.com", timeout=9)
    monkeypatch.setattr(client._opener, "open", fake_urlopen)
    token = client.login("client-id", "client-secret")
    secrets, warnings = client.list_secrets(token, "project-id", "prod", "/hermes", False)

    assert token == "access-value"
    assert secrets == {"ALPHA_API_KEY": "alpha-value", "BETA_TOKEN": "beta-value"}
    assert warnings == []
    assert calls[0][0].full_url.endswith("/api/v1/auth/universal-auth/login")
    assert json.loads(calls[0][0].data) == {
        "clientId": "client-id",
        "clientSecret": "client-secret",
    }
    assert "workspaceId=project-id" in calls[1][0].full_url
    assert calls[1][0].get_header("Authorization") == "Bearer access-value"


def test_http_error_does_not_include_response_body(monkeypatch):
    leaked = "DO_NOT_LEAK_RESPONSE_BODY"

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, io.BytesIO(leaked.encode())
        )

    client = InfisicalClient("https://infisical.example.com")
    monkeypatch.setattr(client._opener, "open", fake_urlopen)

    with pytest.raises(InfisicalClientError) as exc:
        client.login("client-id", "client-secret")

    assert exc.value.kind == ErrorKind.AUTH_FAILED
    assert leaked not in str(exc.value)


@pytest.mark.parametrize(
    ("status", "expected_kind"),
    [
        (401, ErrorKind.AUTH_FAILED),
        (403, ErrorKind.AUTH_FAILED),
        (404, ErrorKind.REF_INVALID),
        (429, ErrorKind.NETWORK),
        (500, ErrorKind.NETWORK),
    ],
)
def test_http_status_mapping(monkeypatch, status, expected_kind):
    client = InfisicalClient("https://infisical.example.com")

    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, status, "failure", {}, None)

    monkeypatch.setattr(client._opener, "open", fail)
    with pytest.raises(InfisicalClientError) as exc:
        client.login("client-id", "client-secret")
    assert exc.value.kind == expected_kind


def test_invalid_json_is_internal(monkeypatch):
    response = FakeResponse({})
    response._data = b"not-json"
    client = InfisicalClient("https://infisical.example.com")
    monkeypatch.setattr(client._opener, "open", lambda request, timeout: response)
    with pytest.raises(InfisicalClientError) as exc:
        client.login("client-id", "client-secret")
    assert exc.value.kind == ErrorKind.INTERNAL


def test_missing_access_token_is_auth_failure(monkeypatch):
    client = InfisicalClient("https://infisical.example.com")
    monkeypatch.setattr(
        client._opener,
        "open",
        lambda request, timeout: FakeResponse({"expiresIn": 7200}),
    )
    with pytest.raises(InfisicalClientError) as exc:
        client.login("client-id", "client-secret")
    assert exc.value.kind == ErrorKind.AUTH_FAILED


def test_missing_secrets_list_is_internal(monkeypatch):
    client = InfisicalClient("https://infisical.example.com")
    monkeypatch.setattr(
        client._opener,
        "open",
        lambda request, timeout: FakeResponse({"imports": []}),
    )
    with pytest.raises(InfisicalClientError) as exc:
        client.list_secrets("token", "project", "prod", "/", False)
    assert exc.value.kind == ErrorKind.INTERNAL


def test_network_error_does_not_include_bootstrap_secret(monkeypatch):
    bootstrap_secret = "bootstrap-secret-do-not-leak"
    client = InfisicalClient("https://infisical.example.com")

    def fail_with_sensitive_reason(request, timeout):
        raise urllib.error.URLError(bootstrap_secret)

    monkeypatch.setattr(client._opener, "open", fail_with_sensitive_reason)
    with pytest.raises(InfisicalClientError) as exc:
        client.login("client-id", bootstrap_secret)

    assert exc.value.kind == ErrorKind.NETWORK
    assert bootstrap_secret not in str(exc.value)


def test_cross_origin_redirect_is_rejected():
    from infisical_source import _SameOriginRedirectHandler

    handler = _SameOriginRedirectHandler()
    request = urllib.request.Request(  # noqa: S310 -- fixed HTTPS test URL
        "https://infisical.example.com/api/v3/secrets/raw",
        headers={"Authorization": "Bearer access-token-do-not-leak"},
    )
    with pytest.raises(InfisicalClientError, match="different origin") as exc:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://attacker.example.net/steal",
        )
    assert exc.value.kind == ErrorKind.NETWORK
    assert "access-token-do-not-leak" not in str(exc.value)


def test_same_origin_redirect_accepts_explicit_default_port_and_keeps_auth():
    from infisical_source import _SameOriginRedirectHandler

    handler = _SameOriginRedirectHandler()
    request = urllib.request.Request(  # noqa: S310 -- fixed HTTPS test URL
        "https://infisical.example.com/api/v3/secrets/raw",
        headers={"Authorization": "Bearer test-access-token"},
    )
    redirected = handler.redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://infisical.example.com:443/api/v3/secrets/raw/",
    )
    assert redirected is not None
    assert redirected.get_header("Authorization") == "Bearer test-access-token"


def test_rejects_insecure_remote_http():
    with pytest.raises(ValueError, match="HTTPS"):
        InfisicalClient("http://infisical.example.com")


def test_local_http_also_requires_explicit_opt_in():
    with pytest.raises(ValueError, match="HTTPS"):
        InfisicalClient("http://127.0.0.1:8080")


def test_allows_explicit_insecure_http():
    assert InfisicalClient(
        "http://172.16.2.4:8080", allow_insecure_http=True
    ).base_url == "http://172.16.2.4:8080"


def test_response_size_cap(monkeypatch):
    class OversizeResponse(FakeResponse):
        def __init__(self):
            self._data = b"x" * 101
            self.status = 200

    client = InfisicalClient("https://infisical.example.com", max_response_bytes=100)
    monkeypatch.setattr(client._opener, "open", lambda request, timeout: OversizeResponse())
    with pytest.raises(InfisicalClientError, match="response exceeded") as exc:
        client.login("client", "secret")
    assert exc.value.kind == ErrorKind.INTERNAL


def test_duplicate_invalid_and_empty_secrets_are_skipped(monkeypatch):
    payload = {"secrets": [
        {"secretKey": "GOOD_TOKEN", "secretValue": "secret-value-a"},
        {"secretKey": "GOOD_TOKEN", "secretValue": "secret-value-b"},
        {"secretKey": "bad-key", "secretValue": "hidden-value"},
        {"secretKey": "EMPTY_KEY", "secretValue": ""},
        {"secretKey": "NON_STRING", "secretValue": 123},
    ]}
    client = InfisicalClient("https://infisical.example.com")
    monkeypatch.setattr(client._opener, "open", lambda request, timeout: FakeResponse(payload))
    secrets, warnings = client.list_secrets("token", "project", "prod", "/", False)

    assert secrets == {"GOOD_TOKEN": "secret-value-a"}
    assert len(warnings) == 4
    rendered = "\n".join(warnings)
    assert "secret-value-a" not in rendered
    assert "secret-value-b" not in rendered
    assert "hidden-value" not in rendered
