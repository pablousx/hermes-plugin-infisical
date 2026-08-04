from __future__ import annotations

import os

import pytest
from agent.secret_sources.registry import _reset_registry_for_tests, apply_all, register_source

from infisical_source import InfisicalSource

pytestmark = pytest.mark.e2e


def test_live_infisical_apply_and_provenance_without_printing_values(tmp_path):
    project_id = os.environ.get("INFISICAL_E2E_PROJECT_ID")
    if not project_id:
        pytest.skip("INFISICAL_E2E_PROJECT_ID is not set")

    config = {
        "sources": ["infisical"],
        "infisical": {
            "enabled": True,
            "project_id": project_id,
            "environment": os.environ.get("INFISICAL_E2E_ENVIRONMENT", "prod"),
            "secret_path": os.environ.get("INFISICAL_E2E_SECRET_PATH", "/"),
            "recursive": os.environ.get("INFISICAL_E2E_RECURSIVE") == "1",
            "allow_insecure_http": os.environ.get("INFISICAL_E2E_ALLOW_INSECURE_HTTP") == "1",
        },
    }

    _reset_registry_for_tests()
    try:
        assert register_source(InfisicalSource())
        target = {}
        report = apply_all(config, tmp_path, environ=target)
        source_report = report.sources[0]

        assert source_report.result.ok, (
            source_report.result.error_kind,
            source_report.result.error,
        )
        assert source_report.result.secrets
        assert len(source_report.applied) == len(source_report.result.secrets)
        assert len(target) == len(source_report.applied)
        assert all(report.provenance[name].source == "infisical" for name in source_report.applied)

        expected_count = os.environ.get("INFISICAL_E2E_EXPECTED_COUNT")
        if expected_count:
            assert len(source_report.result.secrets) == int(expected_count)
    finally:
        _reset_registry_for_tests()
