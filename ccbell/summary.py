"""
ccbell.summary — extract and sanitize the last assistant reply from transcript.jsonl.

Functions:
    extract_last_assistant_text(transcript_path) -> str | None
    sanitize(text) -> str
    truncate(text, max_len, suffix) -> str
    build_summary(transcript_path, max_len, suffix) -> str | None

Input:  path to a Claude Code transcript.jsonl file
Output: sanitized, truncated single-line summary string (or None)
Usage:
    from ccbell.summary import build_summary
    text = build_summary("/path/to/transcript.jsonl", max_len=200)
Created: 2026-04-17
"""

from __future__ import annotations

import json
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# A. Extract last assistant text
# ---------------------------------------------------------------------------

def _is_assistant(record: dict) -> bool:
    """Return True if the record looks like an assistant message (multi-schema)."""
    if record.get("type") == "assistant":
        return True
    if record.get("role") == "assistant":
        return True
    msg = record.get("message")
    if isinstance(msg, dict) and msg.get("role") == "assistant":
        return True
    return False


def _extract_text(record: dict) -> str | None:
    """Extract plain text from a record's content field."""
    # content may be nested under "message"
    content = record.get("content")
    if content is None:
        msg = record.get("message")
        if isinstance(msg, dict):
            content = msg.get("content")

    if content is None:
        return None

    # content is a plain string
    if isinstance(content, str):
        return content if content.strip() else None

    # content is a list of blocks
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text", "")
                if t:
                    parts.append(t)
        return "\n".join(parts) if parts else None

    return None


def extract_last_assistant_text(transcript_path: str | None) -> str | None:
    """Parse transcript.jsonl and return the last assistant message text.

    Returns None when the file is missing, empty, or contains no assistant text.
    Never raises.
    """
    if not transcript_path:
        return None
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None

    last_text: str | None = None
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(record, dict):
            continue
        if _is_assistant(record):
            text = _extract_text(record)
            if text:
                last_text = text

    return last_text


# ---------------------------------------------------------------------------
# B. Sanitize — redact sensitive paths and IPs
# ---------------------------------------------------------------------------

# Order matters: specific patterns first, then generic
_PATH_PATTERNS = [
    (re.compile(r"/home/[^/\\]+"), "~"),
    (re.compile(r"/Users/[^/\\]+"), "~"),
    (re.compile(r"[Cc]:[\\\/][Uu]sers[\\\/][^\\\/]+[\\\/]?"), "~/"),
    (re.compile(r"/root(?=[/\\]|$)"), "~"),
]

_IP_URL_RE = re.compile(r"https?://(\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?")
_WS_RE = re.compile(r"\s+")


def sanitize(text: str) -> str:
    """Redact user paths and literal-IP URLs. Never raises."""
    try:
        for pattern, replacement in _PATH_PATTERNS:
            text = pattern.sub(replacement, text)
        # normalize backslashes to forward slashes after redaction
        text = text.replace("\\", "/")
        text = _IP_URL_RE.sub(lambda m: m.group(0).replace(m.group(1), "<redacted-host>"), text)
        text = _WS_RE.sub(" ", text).strip()
        return text
    except Exception:
        return text


# ---------------------------------------------------------------------------
# C. Truncate
# ---------------------------------------------------------------------------

def truncate(text: str, max_len: int, suffix: str = "...") -> str:
    """Truncate text to max_len characters, appending suffix if truncated."""
    if len(text) <= max_len:
        return text
    if max_len <= len(suffix):
        return suffix[:max_len]
    return text[: max_len - len(suffix)].rstrip() + suffix


# ---------------------------------------------------------------------------
# D. Public entry point
# ---------------------------------------------------------------------------

def build_summary(
    transcript_path: str | None,
    max_len: int = 200,
    suffix: str = "...",
) -> str | None:
    """Extract → sanitize → truncate. Returns None on any failure."""
    raw = extract_last_assistant_text(transcript_path)
    if not raw:
        return None
    cleaned = sanitize(raw)
    if not cleaned:
        return None
    return truncate(cleaned, max_len, suffix)
