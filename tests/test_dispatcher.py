"""
tests/test_dispatcher — minimal tests for ccbell.dispatcher.

Input:  fixtures and monkeypatched stdin
Output: pytest results
Created: 2026-04-17
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

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


class _FakeStdin:
    """Minimal stdin stub for monkeypatching."""

    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text
