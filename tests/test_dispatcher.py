"""
tests/test_dispatcher — minimal tests for ccbell.dispatcher.

Input:  fixtures and monkeypatched stdin
Output: pytest results
Created: 2026-04-17
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from ccbell.config import BackendConfig, RuntimeConfig
from ccbell.dispatcher import main, run

FIXTURES = Path(__file__).parent / "fixtures"


def test_run_with_valid_stop_payload():
    """run() should return 0 for a valid Stop payload."""
    payload = json.loads(
        (FIXTURES / "sample_stop_payload.json").read_text(encoding="utf-8")
    )
    rc = run(payload)
    assert rc == 0


def test_main_with_empty_stdin(monkeypatch):
    """main() should return 0 when stdin is empty."""
    monkeypatch.setattr(sys, "stdin", _FakeStdin(""))
    rc = main()
    assert rc == 0


def test_main_with_invalid_json(monkeypatch):
    """main() should return 0 when stdin contains invalid JSON."""
    monkeypatch.setattr(sys, "stdin", _FakeStdin("not json"))
    rc = main()
    assert rc == 0


def test_run_with_transcript(capsys):
    """run() with a valid transcript should include summary in body."""
    payload = {
        "hook_event_name": "Stop",
        "session_id": "abcdef1234567890",
        "cwd": "/tmp/demo-project",
        "transcript_path": str(FIXTURES / "sample_transcript_basic.jsonl"),
    }
    rc = run(payload)
    assert rc == 0
    captured = capsys.readouterr()
    assert "—— 摘要 ——" in captured.err


def test_run_without_transcript(capsys):
    """run() with a missing transcript should show summary: (none)."""
    payload = {
        "hook_event_name": "Stop",
        "session_id": "abcdef1234567890",
        "cwd": "/tmp/demo-project",
        "transcript_path": "/tmp/__ccbell_no_such_file__.jsonl",
    }
    rc = run(payload)
    assert rc == 0
    captured = capsys.readouterr()
    assert "summary: (none)" in captured.err


def test_dispatcher_invokes_enabled_backends(monkeypatch):
    """Enabled backend should be invoked via subprocess with correct env."""
    calls: list[subprocess.CompletedProcess] = []

    def _mock_run(cmd, **kwargs):
        calls.append(MagicMock(cmd=cmd, kwargs=kwargs))
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", _mock_run)

    # patch load_runtime_config to return a config with a bark backend
    fake_cfg = RuntimeConfig(
        backends=[BackendConfig(name="bark", enabled=True, params={"key": "K"})],
    )
    monkeypatch.setattr("ccbell.dispatcher.load_runtime_config", lambda: fake_cfg)

    payload = {
        "hook_event_name": "Stop",
        "session_id": "abc",
        "cwd": "/tmp/test",
        "transcript_path": "",
    }
    rc = run(payload)
    assert rc == 0
    assert len(calls) == 1
    env = calls[0].kwargs["env"]
    assert "CCBELL_TITLE" in env
    assert "CCBELL_BODY" in env
    assert "CCBELL_BACKEND_CONFIG" in env


def test_dispatcher_skips_unknown_backend(monkeypatch, capsys):
    """Unknown backend name should be skipped with a warning, no crash."""
    fake_cfg = RuntimeConfig(
        backends=[BackendConfig(name="nope", enabled=True, params={})],
    )
    monkeypatch.setattr("ccbell.dispatcher.load_runtime_config", lambda: fake_cfg)

    payload = {
        "hook_event_name": "Stop",
        "session_id": "abc",
        "cwd": "/tmp/test",
        "transcript_path": "",
    }
    rc = run(payload)
    assert rc == 0
    captured = capsys.readouterr()
    assert "none enabled" in captured.err


class _FakeStdin:
    """Minimal stdin stub for monkeypatching."""

    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text
