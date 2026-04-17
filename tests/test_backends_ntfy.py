"""
tests/test_backends_ntfy — tests for ccbell.backends.ntfy.

Uses monkeypatched urllib to avoid real network requests.

Input:  environment variables (CCBELL_TITLE, CCBELL_BODY, etc.)
Output: pytest results
Created: 2026-04-17
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ccbell.backends.ntfy import main


def _set_env(monkeypatch, title="T", body="B", group="G", level="info", config=None):
    """Helper to set invocation env vars."""
    monkeypatch.setenv("CCBELL_TITLE", title)
    monkeypatch.setenv("CCBELL_BODY", body)
    monkeypatch.setenv("CCBELL_GROUP", group)
    monkeypatch.setenv("CCBELL_LEVEL", level)
    if config is None:
        config = {
            "server": "https://ntfy.sh",
            "topic": "ccbell-test-topic",
        }
    monkeypatch.setenv("CCBELL_BACKEND_CONFIG", json.dumps(config))


def _mock_urlopen_ok():
    """Return a mock urlopen that yields HTTP 200."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_ntfy_success(monkeypatch):
    """Mock 200 → main() returns 0, request is POST with correct headers."""
    _set_env(monkeypatch)
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    assert req.method == "POST"
    assert req.get_header("Title") is not None
    assert req.get_header("Priority") is not None
    assert "ccbell-test-topic" in req.full_url


def test_ntfy_missing_topic(monkeypatch):
    """No topic → return 2."""
    _set_env(monkeypatch, config={"server": "https://ntfy.sh"})
    rc = main()
    assert rc == 2


def test_ntfy_missing_server(monkeypatch):
    """No server → return 2."""
    _set_env(monkeypatch, config={"topic": "ccbell-test"})
    rc = main()
    assert rc == 2


def test_ntfy_http_error(monkeypatch):
    """URLError → return 1."""
    _set_env(monkeypatch)
    from urllib.error import URLError
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", side_effect=URLError("fail")):
        rc = main()
    assert rc == 1


def test_ntfy_priority_mapping(monkeypatch):
    """level=error with priority_map → Priority header = 5."""
    config = {
        "server": "https://ntfy.sh",
        "topic": "ccbell-test-topic",
        "priority_map": {"info": 3, "warning": 4, "error": 5},
    }
    _set_env(monkeypatch, level="error", config=config)
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    assert req.get_header("Priority") == "5"


def test_ntfy_unicode_title_fallback(monkeypatch):
    """Non-ASCII title → Title header is URL-encoded, body starts with original title."""
    _set_env(monkeypatch, title="中文标题")
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    # Title header should be percent-encoded (not raw Chinese)
    title_header = req.get_header("Title")
    assert "%" in title_header
    # body should start with the original title line
    body = req.data.decode("utf-8")
    assert body.startswith("标题：中文标题")


def test_ntfy_with_token(monkeypatch):
    """Config with token → Authorization: Bearer <token> header."""
    config = {
        "server": "https://ntfy.sh",
        "topic": "ccbell-test-topic",
        "token": "abc123",
    }
    _set_env(monkeypatch, config=config)
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer abc123"


def test_ntfy_with_tags_list(monkeypatch):
    """Tags as list → comma-joined Tags header."""
    config = {
        "server": "https://ntfy.sh",
        "topic": "ccbell-test-topic",
        "tags": ["bell", "robot"],
    }
    _set_env(monkeypatch, config=config)
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    assert req.get_header("Tags") == "bell,robot"


def test_ntfy_with_tags_csv(monkeypatch):
    """Tags as CSV string → same Tags header."""
    config = {
        "server": "https://ntfy.sh",
        "topic": "ccbell-test-topic",
        "tags": "bell,robot",
    }
    _set_env(monkeypatch, config=config)
    with patch("ccbell.backends.ntfy.urllib.request.urlopen", return_value=_mock_urlopen_ok()) as m:
        rc = main()
    assert rc == 0
    req = m.call_args[0][0]
    assert req.get_header("Tags") == "bell,robot"
