"""
tests/test_summary — tests for ccbell.summary.

Input:  fixture files and inline strings
Output: pytest results
Created: 2026-04-17
"""

import os
from pathlib import Path

from ccbell.summary import (
    build_summary,
    extract_last_assistant_text,
    sanitize,
    truncate,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestExtractLastAssistantText:
    def test_basic(self):
        """Return last assistant text from a normal transcript."""
        path = str(FIXTURES / "sample_transcript_basic.jsonl")
        result = extract_last_assistant_text(path)
        assert result is not None
        assert "Done." in result

    def test_empty_file(self):
        """Return None for an empty transcript file."""
        path = str(FIXTURES / "sample_transcript_empty.jsonl")
        assert extract_last_assistant_text(path) is None

    def test_malformed(self):
        """Skip bad lines, return last valid assistant text."""
        path = str(FIXTURES / "sample_transcript_malformed.jsonl")
        result = extract_last_assistant_text(path)
        assert result == "second good final"

    def test_alt_schema(self):
        """Handle alternative schema (top-level role + content)."""
        path = str(FIXTURES / "sample_transcript_alt_schema.jsonl")
        result = extract_last_assistant_text(path)
        assert result == "alt schema final"

    def test_nonexistent_file(self):
        """Return None for a path that does not exist."""
        assert extract_last_assistant_text("/tmp/__ccbell_no_such_file__.jsonl") is None

    def test_none_path(self):
        """Return None when path is None."""
        assert extract_last_assistant_text(None) is None


class TestSanitize:
    def test_home_path_redaction(self):
        """Redact /home/<user> to ~."""
        text = "see /home/alice/project files"
        result = sanitize(text)
        assert "~/project" in result
        assert "/home/alice" not in result

    def test_windows_path_redaction(self):
        """Redact C:\\Users\\<user> to ~."""
        text = "Done. C:\\Users\\bob\\work finished."
        result = sanitize(text)
        assert "~/work" in result
        assert "C:\\Users" not in result
        assert "bob" not in result

    def test_ip_url_redaction(self):
        """Redact literal IP in URL."""
        text = "see http://192.168.1.10:8080/foo for details"
        result = sanitize(text)
        assert "<redacted-host>" in result
        assert "192.168.1.10" not in result

    def test_whitespace_collapse(self):
        """Collapse multiple whitespace into single space."""
        assert sanitize("hello   world\n\nfoo") == "hello world foo"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", 100) == "hello"

    def test_long_text_truncated(self):
        text = "a" * 500
        result = truncate(text, max_len=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_max_len_smaller_than_suffix(self):
        result = truncate("hello", max_len=2, suffix="...")
        assert len(result) == 2


class TestBuildSummary:
    def test_basic_with_redaction(self):
        """Full pipeline: extract + sanitize + truncate on basic fixture."""
        path = str(FIXTURES / "sample_transcript_basic.jsonl")
        result = build_summary(path, max_len=200)
        assert result is not None
        assert "~/project" in result
        assert "/home/alice" not in result
        assert "~/work" in result
        assert "C:\\Users" not in result

    def test_empty_returns_none(self):
        path = str(FIXTURES / "sample_transcript_empty.jsonl")
        assert build_summary(path) is None
