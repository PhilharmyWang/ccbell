"""
tests/test_backends_bark — tests for ccbell.backends.bark.

Uses monkeypatched urllib to avoid real network requests.

Input:  environment variables (CCBELL_TITLE, CCBELL_BODY, etc.)
Output: pytest results
Created: 2026-04-17
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from ccbell.backends.bark import main


def _set_env(monkeypatch, title="T", body="B", group="G", level="info", config=None):
    """Helper to set invocation env vars."""
    monkeypatch.setenv("CCBELL_TITLE", title)
    monkeypatch.setenv("CCBELL_BODY", body)
    monkeypatch.setenv("CCBELL_GROUP", group)
    monkeypatch.setenv("CCBELL_LEVEL", level)
    if config is None:
        config = {"server": "https://api.day.app", "key": "testkey123"}
    monkeypatch.setenv("CCBELL_BACKEND_CONFIG", json.dumps(config))


def test_bark_success(monkeypatch):
    """Mock urlopen returning 200 → main() returns 0."""
    _set_env(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("ccbell.backends.bark.urllib.request.urlopen", return_value=mock_resp) as m:
        rc = main()

    assert rc == 0
    # verify the URL contains key and encoded title/body
    called_url = m.call_args[0][0].full_url
    assert "testkey123" in called_url


def test_bark_missing_key(monkeypatch):
    """No key in config → main() returns 2."""
    _set_env(monkeypatch, config={"server": "https://api.day.app"})
    rc = main()
    assert rc == 2


def test_bark_http_error(monkeypatch):
    """urlopen raises URLError → main() returns non-0."""
    _set_env(monkeypatch)
    from urllib.error import URLError

    with patch("ccbell.backends.bark.urllib.request.urlopen", side_effect=URLError("fail")):
        rc = main()
    assert rc != 0


def test_level_mapping(monkeypatch):
    """CCBELL_LEVEL=warning + level_map should produce level=timeSensitive in URL."""
    config = {
        "server": "https://api.day.app",
        "key": "testkey123",
        "level_map": {"warning": "timeSensitive"},
    }
    _set_env(monkeypatch, level="warning", config=config)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("ccbell.backends.bark.urllib.request.urlopen", return_value=mock_resp) as m:
        rc = main()

    assert rc == 0
    called_url = m.call_args[0][0].full_url
    assert "level=timeSensitive" in called_url
