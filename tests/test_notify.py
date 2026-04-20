"""
tests/test_notify — core tests for ccbell.notify.

Input:  fixtures + monkeypatched env/urllib
Output: pytest results
Created: 2026-04-17
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ccbell.notify import (
    build_notification,
    extract_summary,
    main,
    sanitize,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── sanitize ────────────────────────────────────────────────────────────────


def test_sanitize_paths():
    """Unix + Windows + IPv4 paths are all redacted."""
    text = "see /home/alice/x and C:\\Users\\bob\\y http://192.168.1.10:8080/z"
    result = sanitize(text)
    assert "~/x" in result
    assert "/home/alice" not in result
    assert "~/y" in result
    assert "bob" not in result
    assert "<redacted-host>" in result
    assert "192.168.1.10" not in result


# ── extract_summary ─────────────────────────────────────────────────────────


def test_extract_summary_basic():
    """Read sample_transcript_basic.jsonl → get last assistant text."""
    path = str(FIXTURES / "sample_transcript_basic.jsonl")
    result = extract_summary(path)
    assert result  # non-empty
    assert "Done" in result
    assert "/home/alice" not in result  # sanitized


def test_extract_summary_empty_file():
    """Empty transcript → empty string."""
    path = str(FIXTURES / "sample_transcript_empty.jsonl")
    assert extract_summary(path) == ""


def test_extract_summary_malformed():
    """Malformed lines are skipped, no exception."""
    path = str(FIXTURES / "sample_transcript_malformed.jsonl")
    result = extract_summary(path)
    assert "second good final" in result


# ── build_notification ──────────────────────────────────────────────────────


def test_build_notification_stop():
    """Stop event → title has ✅, body has project/session/path, default exit=end_turn."""
    payload = {
        "hook_event_name": "Stop",
        "session_id": "abcdef12345678",
        "cwd": "/tmp/demo-project",
        "transcript_path": "",
    }
    title, body, level = build_notification(payload)
    assert "✅" in title
    assert "demo-project" in body
    assert "abcdef12" in body
    assert "退出：end_turn" in body
    assert "active" == level


def test_build_notification_notification():
    """Notification event → title has ⚠️, level=timeSensitive, no exit line."""
    payload = {
        "hook_event_name": "Notification",
        "session_id": "xyz",
        "cwd": "/tmp/test",
        "transcript_path": "",
    }
    title, body, level = build_notification(payload)
    assert "⚠️" in title
    assert "timeSensitive" == level
    assert "退出：" not in body


# ── stop_reason ────────────────────────────────────────────────────────────


def test_stop_reason_error():
    payload = {
        "hook_event_name": "Stop", "session_id": "x", "cwd": "/tmp",
        "transcript_path": "", "stop_reason": "error",
    }
    title, body, level = build_notification(payload)
    assert "❌" in title
    assert "出错退出" in title
    assert "timeSensitive" == level
    assert "退出：error" in body


def test_stop_reason_user_interrupted():
    payload = {
        "hook_event_name": "Stop", "session_id": "x", "cwd": "/tmp",
        "transcript_path": "", "stop_reason": "user_interrupted",
    }
    title, body, level = build_notification(payload)
    assert "🛑" in title
    assert "已中断" in title
    assert "active" == level


def test_stop_reason_max_tokens():
    payload = {
        "hook_event_name": "Stop", "session_id": "x", "cwd": "/tmp",
        "transcript_path": "", "stop_reason": "max_tokens",
    }
    title, body, level = build_notification(payload)
    assert "⚠️" in title
    assert "超长截断" in title
    assert "timeSensitive" == level


def test_stop_reason_end_turn_default():
    payload = {
        "hook_event_name": "Stop", "session_id": "x", "cwd": "/tmp",
        "transcript_path": "",
    }
    title, body, level = build_notification(payload)
    assert "✅" in title
    assert "退出：end_turn" in body


# ── main (dry-run + duration filter) ────────────────────────────────────────


def test_main_dry_run(monkeypatch):
    """CCBELL_DRY_RUN=1 → no urlopen call, exit 0."""
    monkeypatch.setattr("ccbell.notify.DRY_RUN", True)
    monkeypatch.setattr("ccbell.notify.BARK_KEY", "testkey")
    monkeypatch.setattr("sys.stdin", _FakeStdin(
        json.dumps({"hook_event_name": "Stop", "session_id": "abc", "cwd": "/tmp", "transcript_path": ""})
    ))
    with patch("ccbell.notify.urllib.request.urlopen") as m:
        rc = main()
    assert rc == 0
    m.assert_not_called()


def test_main_below_min_duration(monkeypatch):
    """MIN_DURATION=60, payload duration=10 → skip push, exit 0."""
    monkeypatch.setattr("ccbell.notify.MIN_DURATION", 60)
    monkeypatch.setattr("ccbell.notify.BARK_KEY", "testkey")
    monkeypatch.setattr("sys.stdin", _FakeStdin(
        json.dumps({"hook_event_name": "Stop", "session_id": "abc", "cwd": "/tmp",
                     "transcript_path": "", "duration_seconds": 10})
    ))
    with patch("ccbell.notify.urllib.request.urlopen") as m:
        rc = main()
    assert rc == 0
    m.assert_not_called()


class _FakeStdin:
    def __init__(self, text: str):
        self._text = text
    def read(self) -> str:
        return self._text
