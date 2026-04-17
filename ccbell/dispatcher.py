"""
ccbell.dispatcher — core dispatch logic for Claude Code hook events.

Reads a hook payload (JSON dict), assembles notification fields, and logs them.
Step 1: dry-run only (no real backend invocation).

Input:  payload dict with keys: hook_event_name, session_id, cwd, transcript_path
Output: int exit code (always 0 in Step 1)
Usage:
    from ccbell.dispatcher import run, main
    rc = run({"hook_event_name": "Stop", "session_id": "abc", ...})
Created: 2026-04-17
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from ccbell.config import load_runtime_config
from ccbell.logger import get_logger
from ccbell.summary import build_summary

log = get_logger("ccbell.dispatcher")

_TITLE_MAP = {
    "Stop": "✅ [{device}] Claude Code 完成",
    "Notification": "🔔 [{device}] Claude Code 待确认",
    "SubagentStop": "🧩 [{device}] 子代理完成",
}


def _make_title(event: str, device: str) -> str:
    template = _TITLE_MAP.get(event, "ℹ️ [{device}] {event}")
    return template.format(device=device, event=event)


def run(payload: dict) -> int:
    """Assemble notification fields from payload and log them. Returns 0."""
    cfg = load_runtime_config()

    event = payload.get("hook_event_name") or "Unknown"
    session_id = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    transcript_path = payload.get("transcript_path") or ""

    project_name = Path(cwd).name if cwd else "unknown"
    short_sid = session_id[:8] if session_id else "--------"
    now = datetime.now().strftime("%H:%M:%S")

    title = _make_title(event, cfg.device_name)
    body = (
        f"项目：{project_name}\n"
        f"会话：{short_sid}  时间：{now}\n"
        f"路径：{cwd}"
    )
    group = f"ccbell-{cfg.device_name}"
    level = "warning" if event == "Notification" else "info"

    # --- summary (Step 2) ---
    summary = None
    try:
        summary = build_summary(
            transcript_path or None,
            max_len=cfg.summary_max_length,
            suffix=cfg.summary_truncate_suffix,
        )
    except Exception as exc:
        log.warning("summary extraction failed: %s", exc)

    if summary:
        body += "\n—— 摘要 ——\n" + summary

    # --- output to stderr ---
    print(f"CCBELL_TITLE={title}", file=sys.stderr)
    print(f"CCBELL_BODY={body}", file=sys.stderr)
    print(f"CCBELL_GROUP={group}", file=sys.stderr)
    print(f"CCBELL_LEVEL={level}", file=sys.stderr)
    if summary:
        print(f"summary: {summary}", file=sys.stderr)
    else:
        print("summary: (none)", file=sys.stderr)
    print("backends: (dry-run, none invoked)", file=sys.stderr)

    # --- output to log file ---
    log.info("event=%s session=%s project=%s", event, short_sid, project_name)
    log.debug("title=%s body=%s group=%s level=%s summary=%s", title, body, group, level, summary)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point: read JSON from stdin, call run(), never crash."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        payload = {}

    try:
        return run(payload)
    except Exception as exc:
        log.error("dispatcher failed: %s", exc)
        return 0
