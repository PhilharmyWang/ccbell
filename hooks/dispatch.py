#!/usr/bin/env python3
"""hooks/dispatch.py — Claude Code hook entry point.

Input:  JSON via stdin (from Claude Code hook)
Output: exit code 0 (never blocks Claude Code)
Created: 2026-04-17
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccbell.notify import main

sys.exit(main())
