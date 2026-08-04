from __future__ import annotations

from agent.secret_sources.registry import _reset_registry_for_tests, apply_all, register_source

from infisical_source import InfisicalSource


def test_bootstrap_variables_are_protected():
    protected = InfisicalSource().protected_env_vars({})
    assert protected == frozenset(InfisicalSource.BOOTSTRAP_ENV_VARS)


def test_config_schema_never_requests_secret_values_in_config():
    schema = InfisicalSource().config_schema()
    assert "client_secret" not in schema
    assert "client_id" not in schema
    assert "project_id" in schema


def test_orchestrator_never_applies_bootstrap_values(monkeypatch, tmp_path):
    monkeypatch.setenv("INFISICAL_HOST_URL", "https://infisical.example.com")
    monkeypatch.setenv("INFISICAL_UNIVERSAL_AUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET", "client-secret")

    class StubClient:
        def login(self, client_id, client_secret):
            return "access-token"

        def list_secrets(self, *args):
            return {
                "INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET": "vault-copy",
                "SERVICE_API_KEY": "service-value",
            }, []

    source = InfisicalSource(client_factory=lambda **kwargs: StubClient())
    _reset_registry_for_tests()
    try:
        register_source(source)
        target = {}
        report = apply_all(
            {
                "sources": ["infisical"],
                "infisical": {"enabled": True, "project_id": "project"},
            },
            tmp_path,
            environ=target,
        )
        assert target == {"SERVICE_API_KEY": "service-value"}
        assert report.sources[0].skipped_protected == [
            "INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET"
        ]
    finally:
        _reset_registry_for_tests()
