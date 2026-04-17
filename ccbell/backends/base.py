"""
ccbell.backends.base — shared utilities for backend scripts.

Provides helpers for reading invocation environment variables and error exit.

Input:  environment variables set by dispatcher
Output: parsed env dict / error exit
Usage:
    from ccbell.backends.base import read_invocation_env, die
Created: 2026-04-17
"""

from __future__ import annotations

import json
import os
import sys


def read_invocation_env() -> dict:
    """Read CCBELL_* invocation variables set by the dispatcher.

    Returns a dict with keys:
        title, body, group, level, backend_config
    Missing values default to empty string / empty dict.
    """
    raw_config = os.environ.get("CCBELL_BACKEND_CONFIG", "")
    try:
        backend_config = json.loads(raw_config) if raw_config else {}
    except (json.JSONDecodeError, ValueError):
        backend_config = {}

    return {
        "title": os.environ.get("CCBELL_TITLE", ""),
        "body": os.environ.get("CCBELL_BODY", ""),
        "group": os.environ.get("CCBELL_GROUP", ""),
        "level": os.environ.get("CCBELL_LEVEL", "info"),
        "backend_config": backend_config,
    }


def die(msg: str, code: int = 1) -> None:
    """Print msg to stderr and exit with code."""
    print(f"ccbell backend error: {msg}", file=sys.stderr)
    sys.exit(code)
