#!/usr/bin/env python3
"""scripts/_patch_settings.py — Upsert ccbell hooks & env into Claude Code settings.json.

Pure stdlib. Called by install.ps1 / install.sh.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for emoji output
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, io.UnsupportedOperation):
    pass


def find_settings_path() -> Path:
    """Default to ~/.claude/settings.json."""
    return Path.home() / ".claude" / "settings.json"


def mask_secret(value: str) -> str:
    """Show first 4 and last 4 chars, mask the rest."""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def load_or_create(path: Path) -> dict:
    """Load JSON or return empty dict."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def backup(path: Path) -> Path | None:
    """Timestamp backup. Returns backup path or None if file didn't exist."""
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = path.with_name(path.name.replace(".json", f".json.bak-{ts}"))
    shutil.copy2(path, bak)
    return bak


def clean_old_hooks(hooks: dict) -> None:
    """Remove old powershell.exe / windows-notification.ps1 entries."""
    for event_name, matcher_list in list(hooks.items()):
        if not isinstance(matcher_list, list):
            continue
        for matcher_entry in matcher_list:
            if not isinstance(matcher_entry, dict):
                continue
            inner = matcher_entry.get("hooks", [])
            if not isinstance(inner, list):
                continue
            matcher_entry["hooks"] = [
                h for h in inner
                if not (
                    isinstance(h, dict)
                    and "command" in h
                    and (
                        "powershell.exe" in h["command"]
                        or "windows-notification.ps1" in h["command"]
                    )
                )
            ]


def upsert_hook(hooks: dict, event_name: str, command: str) -> None:
    """Upsert a ccbell hook entry for the given event."""
    if event_name not in hooks or not isinstance(hooks[event_name], list):
        hooks[event_name] = []

    # Find or create a matcher="" entry
    matcher_entry = None
    for entry in hooks[event_name]:
        if isinstance(entry, dict) and entry.get("matcher", "") == "":
            matcher_entry = entry
            break

    if matcher_entry is None:
        matcher_entry = {"matcher": "", "hooks": []}
        hooks[event_name].append(matcher_entry)

    if "hooks" not in matcher_entry or not isinstance(matcher_entry["hooks"], list):
        matcher_entry["hooks"] = []

    command_norm = command.replace("\\", "/")

    # Check if exact command already exists
    for h in matcher_entry["hooks"]:
        if isinstance(h, dict) and "command" in h:
            if h["command"].replace("\\", "/") == command_norm:
                return  # Already present, nothing to do

    # Remove any old ccbell dispatch.py entries then add new one
    matcher_entry["hooks"] = [
        h for h in matcher_entry["hooks"]
        if not (
            isinstance(h, dict)
            and "command" in h
            and "dispatch.py" in h["command"]
        )
    ]
    matcher_entry["hooks"].append({"type": "command", "command": command})


def upsert_env(settings: dict, key: str, value: str) -> None:
    """Upsert an env var in settings."""
    if "env" not in settings or not isinstance(settings["env"], dict):
        settings["env"] = {}
    settings["env"][key] = value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upsert ccbell hooks into Claude Code settings.json"
    )
    parser.add_argument("--settings-path", default=None,
                        help="Path to settings.json (default: auto)")
    parser.add_argument("--dispatch-path", required=True,
                        help="Absolute path to hooks/dispatch.py")
    parser.add_argument("--python-bin", default="python",
                        help="Python binary (default: python, Linux uses python3)")
    parser.add_argument("--bark-key", required=True,
                        help="Bark key (required)")
    parser.add_argument("--device-name", required=True,
                        help="Device name (required)")
    parser.add_argument("--device-emoji", required=True,
                        help="Device emoji (required)")
    parser.add_argument("--bark-server", default="",
                        help="Bark server URL (default: built-in https://api.day.app)")
    parser.add_argument("--zai-token", default="",
                        help="Anthropic auth token (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write to disk")
    args = parser.parse_args()

    # Validate required args are non-empty
    if not args.bark_key.strip():
        print("ERROR: --bark-key must not be empty", file=sys.stderr)
        sys.exit(1)
    if not args.device_name.strip():
        print("ERROR: --device-name must not be empty", file=sys.stderr)
        sys.exit(1)
    if not args.device_emoji.strip():
        print("ERROR: --device-emoji must not be empty", file=sys.stderr)
        sys.exit(1)

    settings_path = Path(args.settings_path) if args.settings_path else find_settings_path()
    dispatch_path = args.dispatch_path.replace("\\", "/")
    command = f"{args.python_bin} {dispatch_path}"

    # Load
    settings = load_or_create(settings_path)
    if "hooks" not in settings or not isinstance(settings["hooks"], dict):
        settings["hooks"] = {}

    # Clean old entries
    clean_old_hooks(settings["hooks"])

    # Upsert hooks for three events
    for event in ("Stop", "Notification", "SubagentStop"):
        upsert_hook(settings["hooks"], event, command)

    # Upsert env
    upsert_env(settings, "BARK_KEY", args.bark_key)
    upsert_env(settings, "CCBELL_DEVICE_NAME", args.device_name)
    upsert_env(settings, "CCBELL_DEVICE_EMOJI", args.device_emoji)
    if args.bark_server.strip():
        upsert_env(settings, "BARK_SERVER", args.bark_server)
    if args.zai_token.strip():
        upsert_env(settings, "ANTHROPIC_AUTH_TOKEN", args.zai_token)

    # Print summary
    action = "将要写入" if args.dry_run else "已写入"
    print(f"\n{action} {settings_path}:")
    print(f"  hooks: Stop, Notification, SubagentStop -> {command}")
    env_keys = ("BARK_KEY", "CCBELL_DEVICE_NAME", "CCBELL_DEVICE_EMOJI",
                "BARK_SERVER", "ANTHROPIC_AUTH_TOKEN")
    for k in env_keys:
        v = settings.get("env", {}).get(k)
        if v is None:
            continue
        if k in ("BARK_KEY", "ANTHROPIC_AUTH_TOKEN"):
            print(f"  env.{k} = {mask_secret(v)}")
        else:
            display_v = v if len(v) <= 40 else v[:37] + "..."
            print(f"  env.{k} = {display_v}")

    if args.dry_run:
        print("\ndry-run: 未写入磁盘")
        return

    # Backup and write
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    bak = backup(settings_path)
    if bak:
        print(f"  备份: {bak}")

    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("  写入完成")


if __name__ == "__main__":
    main()
