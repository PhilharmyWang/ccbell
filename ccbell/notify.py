"""
ccbell.notify — minimal Claude Code → iPhone notifier via Bark.

Single-file core: config from env vars, transcript summary, path redaction, Bark push.
Designed for ML/SSH users who just want a push when Claude Code finishes or needs input.

Input:  JSON payload via stdin (from Claude Code hook)
Output: push notification to Bark; always exits 0 (never blocks Claude Code)
Usage:
    echo '{"hook_event_name":"Stop","session_id":"abc","cwd":"/tmp/project","transcript_path":""}' \
      | CCBELL_DRY_RUN=1 python -m ccbell
    # or:
    echo '...' | python hooks/dispatch.py
Created: 2026-04-17
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

# ── Configuration (env vars, no YAML) ────────────────────────────────────────

BARK_KEY: str = os.environ.get("BARK_KEY", "")
BARK_SERVER: str = os.environ.get("BARK_SERVER", "https://api.day.app")
DEVICE_NAME: str = os.environ.get("CCBELL_DEVICE_NAME") or socket.gethostname()
DEVICE_EMOJI: str = os.environ.get("CCBELL_DEVICE_EMOJI", "💻")
GROUP: str = os.environ.get("CCBELL_GROUP", f"ccbell-{DEVICE_NAME}")
DEBUG: bool = os.environ.get("CCBELL_DEBUG", "") == "1"
DRY_RUN: bool = os.environ.get("CCBELL_DRY_RUN", "") == "1"


def _safe_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


MIN_DURATION: int = _safe_int("CCBELL_MIN_DURATION_SECONDS", 0)
SUMMARY_MAX: int = _safe_int("CCBELL_SUMMARY_MAX_LENGTH", 200)

# ── Logging (minimal, ~10 lines) ────────────────────────────────────────────

log = logging.getLogger("ccbell")
if not log.handlers:
    log.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    try:
        log_dir = Path.home() / ".ccbell"
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / "ccbell.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        pass

# ── Summary extraction & sanitization ────────────────────────────────────────

_PATH_PATTERNS = [
    (re.compile(r"/home/[^/\\]+"), "~"),
    (re.compile(r"/Users/[^/\\]+"), "~"),
    (re.compile(r"[Cc]:[\\\/][Uu]sers[\\\/][^\\\/]+[\\\/]?"), "~/"),
    (re.compile(r"/root(?=[/\\]|$)"), "~"),
]
_IP_URL_RE = re.compile(r"https?://(\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?")
_WS_RE = re.compile(r"\s+")


def sanitize(text: str) -> str:
    """Redact user paths and literal-IP URLs."""
    try:
        for pat, repl in _PATH_PATTERNS:
            text = pat.sub(repl, text)
        text = text.replace("\\", "/")
        text = _IP_URL_RE.sub(lambda m: m.group(0).replace(m.group(1), "<redacted-host>"), text)
        return _WS_RE.sub(" ", text).strip()
    except Exception:
        return text


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    if max_len <= len(suffix):
        return suffix[:max_len]
    return text[: max_len - len(suffix)].rstrip() + suffix


def _is_assistant(rec: dict) -> bool:
    return (rec.get("type") == "assistant" or rec.get("role") == "assistant"
            or (isinstance(rec.get("message"), dict) and rec["message"].get("role") == "assistant"))


def _extract_text(rec: dict) -> str | None:
    content = rec.get("content")
    if content is None and isinstance(rec.get("message"), dict):
        content = rec["message"].get("content")
    if isinstance(content, str):
        return content if content.strip() else None
    if isinstance(content, list):
        parts = [i["text"] for i in content if isinstance(i, dict) and i.get("type") == "text" and i.get("text")]
        return "\n".join(parts) if parts else None
    return None


def extract_summary(transcript_path: str | None) -> str:
    """Return sanitized+truncated last assistant text, or empty string."""
    if not transcript_path:
        return ""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    last: str | None = None
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(rec, dict) and _is_assistant(rec):
            t = _extract_text(rec)
            if t:
                last = t
    if not last:
        return ""
    cleaned = sanitize(last)
    return truncate(cleaned, SUMMARY_MAX) if cleaned else ""

# ── Event presets ────────────────────────────────────────────────────────────

EVENT_PRESETS: dict[str, dict] = {
    "Stop":         {"emoji": "✅", "label": "完成",       "level": "active"},
    "SubagentStop": {"emoji": "🤖", "label": "子任务完成", "level": "active"},
    "Notification": {"emoji": "⚠️", "label": "需要确认",   "level": "timeSensitive"},
}
_UNKNOWN_PRESET = {"emoji": "🔔", "label": "事件", "level": "active"}

# ── Bark push ────────────────────────────────────────────────────────────────


def push_bark(title: str, body: str, level: str) -> None:
    """Send notification via Bark. Silent on failure."""
    if not BARK_KEY:
        log.debug("BARK_KEY not set, skip push")
        return
    if DRY_RUN:
        print(f"[dry-run] title={title}", file=sys.stderr)
        print(f"[dry-run] body={body}", file=sys.stderr)
        print(f"[dry-run] group={GROUP} level={level}", file=sys.stderr)
        return
    try:
        enc_t = urllib.parse.quote(title, safe="")
        enc_b = urllib.parse.quote(body, safe="")
        url = f"{BARK_SERVER}/{BARK_KEY}/{enc_t}/{enc_b}?group={GROUP}&level={level}&sound=bell"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if 200 <= resp.status < 300:
                log.info("bark push ok")
            else:
                log.warning("bark HTTP %d", resp.status)
    except Exception as exc:
        log.warning("bark failed: %s", exc)

# ── Build notification ───────────────────────────────────────────────────────


def build_notification(payload: dict) -> tuple[str, str, str]:
    """Assemble (title, body, level) from hook payload."""
    event = payload.get("hook_event_name") or "Unknown"
    session_id = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    transcript_path = payload.get("transcript_path") or ""

    project = Path(cwd).name if cwd else "unknown"
    preset = EVENT_PRESETS.get(event, _UNKNOWN_PRESET)
    now = datetime.now().strftime("%H:%M:%S")
    short_sid = session_id[:8] if session_id else "--------"

    title = f"{preset['emoji']} [{DEVICE_EMOJI}{DEVICE_NAME}] {preset['label']}"
    lines = [
        f"项目：{project}",
        f"会话：{short_sid}  时间：{now}",
        f"路径：{sanitize(cwd)}",
    ]

    summary = extract_summary(transcript_path)
    if summary:
        lines += ["", "—— 摘要 ——", summary]

    # Optional: uncomment to append context (git branch, GPU, Slurm)
    # from ccbell.enrich import build_context
    # ctx = build_context(cwd)
    # if ctx:
    #     lines += ["", "—— 环境 ——", ctx]

    body = "\n".join(lines)
    return title, body, preset["level"]

# ── Main entry ───────────────────────────────────────────────────────────────


def main() -> int:
    """Read stdin JSON, build notification, push. Always returns 0."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        log.warning("failed to parse stdin payload")
        payload = {}

    try:
        # duration filter
        if MIN_DURATION > 0:
            dur = payload.get("duration_seconds", 0)
            try:
                dur = float(dur)
            except (ValueError, TypeError):
                dur = 0
            if 0 < dur < MIN_DURATION:
                log.info("below min duration (%.0f < %d), skip", dur, MIN_DURATION)
                return 0

        title, body, level = build_notification(payload)
        push_bark(title, body, level)
    except Exception as exc:
        log.error("notify failed: %s", exc)

    return 0
