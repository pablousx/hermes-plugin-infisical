from __future__ import annotations

import shutil
from pathlib import Path

from agent.secret_sources.registry import _reset_registry_for_tests, get_source
from hermes_cli.plugins import PluginManager


def test_real_plugin_loader_registers_source(monkeypatch, tmp_path):
    plugin_root = Path(__file__).resolve().parents[1]
    installed = tmp_path / "plugins" / "infisical"
    installed.mkdir(parents=True)
    for name in ("plugin.yaml", "__init__.py", "infisical_source.py"):
        shutil.copy2(plugin_root / name, installed / name)

    (tmp_path / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - infisical\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    bundled = tmp_path / "bundled-plugins"
    bundled.mkdir()
    monkeypatch.setattr("hermes_cli.plugins.get_bundled_plugins_dir", lambda: bundled)
    monkeypatch.setattr(PluginManager, "_scan_entry_points", lambda self: [])
    _reset_registry_for_tests()
    try:
        manager = PluginManager()
        manager.discover_and_load()
        loaded = {item["key"]: item for item in manager.list_plugins()}
        assert loaded["infisical"]["enabled"] is True
        assert loaded["infisical"]["error"] is None
        source = get_source("infisical")
        assert source is not None
        assert source.label == "Infisical"
    finally:
        _reset_registry_for_tests()
