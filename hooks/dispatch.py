#!/usr/bin/env python3
"""
hooks/dispatch.py — Claude Code hook entry point.

Adds the repository root to sys.path so that `ccbell` package is importable,
then delegates to ccbell.dispatcher.main().

Input:  JSON via stdin (from Claude Code hook)
Output: exit code 0 (never blocks Claude Code)
Usage:
    echo '{"hook_event_name":"Stop"}' | python3 hooks/dispatch.py
    # or: echo '{"hook_event_name":"Stop"}' | python -m ccbell
Created: 2026-04-17
"""

import sys
from pathlib import Path

# add repo root (parent of hooks/) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccbell.dispatcher import main  # noqa: E402

sys.exit(main())
