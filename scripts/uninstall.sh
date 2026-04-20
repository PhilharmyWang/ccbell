#!/usr/bin/env bash
# scripts/uninstall.sh — Remove ccbell hooks & env from Claude Code settings.json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNINSTALL_PY="$SCRIPT_DIR/_uninstall_settings.py"

PY="python3"
if ! command -v python3 &>/dev/null; then
    PY="python"
fi

exec $PY "$UNINSTALL_PY" "$@"
