"""
tests/test_config — tests for ccbell.config.

Input:  temp config.yaml files + environment variables
Output: pytest results
Created: 2026-04-17
"""

import os
from pathlib import Path

import pytest

from ccbell.config import load_runtime_config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove all CCBELL_* env vars before each test."""
    for key in list(os.environ):
        if key.startswith("CCBELL_"):
            monkeypatch.delenv(key, raising=False)


def test_load_with_no_config_file(tmp_path, monkeypatch):
    """No config.yaml and no env → returns defaults."""
    monkeypatch.chdir(tmp_path)
    cfg = load_runtime_config()
    assert cfg.device.name  # should default to hostname
    assert cfg.backends == []
    assert cfg.source_path == ""


def test_load_from_cwd(tmp_path, monkeypatch):
    """config.yaml in cwd should be loaded."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "device:\n  name: workstation\n  group: cluster\n"
        "backends:\n  - name: bark\n    enabled: true\n    key: TEST_KEY\n"
        "enrichers: []\n"
        "filters:\n  min_duration_seconds: 60\n"
        "summary:\n  max_length: 100\n  truncate_suffix: '...'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_runtime_config()
    assert cfg.device.name == "workstation"
    assert cfg.device.group == "cluster"
    assert len(cfg.backends) == 1
    assert cfg.backends[0].name == "bark"
    assert cfg.backends[0].params["key"] == "TEST_KEY"
    assert cfg.filters.min_duration_seconds == 60
    assert cfg.summary.max_length == 100
    assert cfg.source_path == str(cfg_file)


def test_load_with_env_override(tmp_path, monkeypatch):
    """CCBELL_DEVICE_NAME env overrides YAML value."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "device:\n  name: laptop\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CCBELL_DEVICE_NAME", "override")
    cfg = load_runtime_config()
    assert cfg.device.name == "override"


def test_malformed_yaml_falls_back_to_default(tmp_path, monkeypatch):
    """Malformed YAML should not raise; returns defaults."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("{{{{invalid yaml:::", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cfg = load_runtime_config()
    assert cfg.device.name  # falls back to hostname
    assert cfg.backends == []
