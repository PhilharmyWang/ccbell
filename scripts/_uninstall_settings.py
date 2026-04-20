#!/usr/bin/env python3
"""scripts/_uninstall_settings.py — Remove ccbell hooks & env from Claude Code settings.json.

Pure stdlib. Called by uninstall.ps1 / uninstall.sh.
Removes Stop/Notification/SubagentStop hooks containing dispatch.py.
Removes BARK_*/CCBELL_* env keys (keeps ANTHROPIC_AUTH_TOKEN).
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove ccbell hooks & env from Claude Code settings.json"
    )
    parser.add_argument("--settings-path", default=None,
                        help="Path to settings.json (default: auto)")
    args = parser.parse_args()

    settings_path = (
        Path(args.settings_path)
        if args.settings_path
        else Path.home() / ".claude" / "settings.json"
    )

    if not settings_path.exists():
        print(f"No settings.json at {settings_path}, nothing to do.")
        return

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        print(f"WARNING: {settings_path} is not valid JSON, skipping.")
        return

    # Backup
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = settings_path.with_name(settings_path.name.replace(".json", f".json.bak-{ts}"))
    shutil.copy2(settings_path, bak)
    print(f"备份: {bak}")

    # Remove hooks
    hooks = settings.get("hooks", {})
    for event in ("Stop", "Notification", "SubagentStop"):
        if event not in hooks:
            continue
        if isinstance(hooks[event], list):
            for matcher_entry in hooks[event]:
                if isinstance(matcher_entry, dict) and isinstance(matcher_entry.get("hooks"), list):
                    matcher_entry["hooks"] = [
                        h for h in matcher_entry["hooks"]
                        if not (isinstance(h, dict) and "command" in h
                                and "dispatch.py" in h["command"])
                    ]
            hooks[event] = [e for e in hooks[event]
                            if isinstance(e, dict) and e.get("hooks")]
            if not hooks[event]:
                del hooks[event]
        else:
            del hooks[event]

    if not hooks:
        settings.pop("hooks", None)

    # Remove env keys (BARK_*, CCBELL_* — keep ANTHROPIC_AUTH_TOKEN)
    env = settings.get("env", {})
    keys_to_remove = [k for k in env if k.startswith("BARK_") or k.startswith("CCBELL_")]
    for k in keys_to_remove:
        del env[k]
    if not env:
        settings.pop("env", None)

    # Write back
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"已从 {settings_path} 移除 ccbell 相关配置")


if __name__ == "__main__":
    main()
