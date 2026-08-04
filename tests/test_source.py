from __future__ import annotations

import pytest
from agent.secret_sources.base import ErrorKind, FetchResult

from infisical_source import InfisicalClientError, InfisicalSource


class StubClient:
    def __init__(self, *, login_error=None, list_error=None):
        self.login_error = login_error
        self.list_error = list_error

    def login(self, client_id, client_secret):
        if self.login_error:
            raise self.login_error
        return "temporary-access-token"

    def list_secrets(self, token, project_id, environment, secret_path, recursive):
        if self.list_error:
            raise self.list_error
        return {"SERVICE_API_KEY": "service-value"}, ["safe warning"]


def configured_env(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST_URL", "https://infisical.example.com")
    monkeypatch.setenv("INFISICAL_UNIVERSAL_AUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET", "client-secret")


def test_disabled_source_does_not_contact_infisical(tmp_path):
    source = InfisicalSource(client_factory=lambda **kwargs: pytest.fail("must not connect"))
    result = source.fetch({}, tmp_path)
    assert isinstance(result, FetchResult)
    assert result.ok
    assert result.secrets == {}


def test_missing_bootstrap_is_not_configured(monkeypatch, tmp_path):
    for name in InfisicalSource.BOOTSTRAP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    result = InfisicalSource().fetch(
        {"enabled": True, "project_id": "project"}, tmp_path
    )
    assert result.error_kind == ErrorKind.NOT_CONFIGURED
    assert result.secrets == {}


def test_missing_project_is_not_configured(monkeypatch, tmp_path):
    configured_env(monkeypatch)
    result = InfisicalSource().fetch({"enabled": True}, tmp_path)
    assert result.error_kind == ErrorKind.NOT_CONFIGURED


def test_fetch_returns_secrets_and_warnings(monkeypatch, tmp_path):
    configured_env(monkeypatch)
    stub = StubClient()
    source = InfisicalSource(client_factory=lambda **kwargs: stub)
    result = source.fetch(
        {
            "enabled": True,
            "project_id": "project",
            "environment": "prod",
            "secret_path": "hermes",
        },
        tmp_path,
    )
    assert result.ok
    assert result.secrets == {"SERVICE_API_KEY": "service-value"}
    assert result.warnings == ["safe warning"]


def test_client_error_maps_to_fetch_result(monkeypatch, tmp_path):
    configured_env(monkeypatch)
    error = InfisicalClientError(ErrorKind.NETWORK, "Infisical network request failed")
    source = InfisicalSource(client_factory=lambda **kwargs: StubClient(login_error=error))
    result = source.fetch({"enabled": True, "project_id": "project"}, tmp_path)
    assert result.error_kind == ErrorKind.NETWORK
    assert result.error == "Infisical network request failed"


def test_fetch_never_raises_unexpected_error(monkeypatch, tmp_path):
    configured_env(monkeypatch)

    def broken_factory(**kwargs):
        raise RuntimeError("unexpected internal detail")

    result = InfisicalSource(client_factory=broken_factory).fetch(
        {"enabled": True, "project_id": "project"}, tmp_path
    )
    assert result.error_kind == ErrorKind.INTERNAL
    assert result.error == "Infisical secret source failed internally"


def test_override_existing_defaults_true():
    source = InfisicalSource()
    assert source.override_existing({}) is True
    assert source.override_existing({"override_existing": False}) is False
    assert source.override_existing({"override_existing": "false"}) is False
    assert source.override_existing(None) is False


def test_path_normalization(monkeypatch, tmp_path):
    configured_env(monkeypatch)
    captured = {}

    class CapturingClient(StubClient):
        def list_secrets(self, token, project_id, environment, secret_path, recursive):
            captured.update(path=secret_path, env=environment, recursive=recursive)
            return {}, []

    source = InfisicalSource(client_factory=lambda **kwargs: CapturingClient())
    result = source.fetch(
        {
            "enabled": True,
            "project_id": "project",
            "secret_path": "nested/path/",
            "environment": "staging",
            "recursive": True,
        }, tmp_path
    )
    assert result.ok
    assert captured == {"path": "/nested/path", "env": "staging", "recursive": True}


def test_malformed_boolean_fails_cleanly(monkeypatch, tmp_path):
    configured_env(monkeypatch)
    result = InfisicalSource().fetch(
        {"enabled": True, "project_id": "project", "recursive": "yes"}, tmp_path
    )
    assert result.error_kind == ErrorKind.NOT_CONFIGURED
