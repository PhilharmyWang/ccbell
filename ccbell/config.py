"""
ccbell.config — runtime configuration from environment variables.

Step 3 will introduce config.yaml and replace most env-var reading.
For now, this module only reads CCBELL_* environment variables.

Input:  CCBELL_DEVICE_NAME, CCBELL_BACKENDS, CCBELL_DEBUG, CCBELL_MIN_DURATION_SECONDS
Output: RuntimeConfig dataclass
Usage:
    from ccbell.config import load_runtime_config
    cfg = load_runtime_config()
Created: 2026-04-17
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field


@dataclass
class RuntimeConfig:
    """Minimal runtime configuration sourced from environment variables."""

    device_name: str = ""
    backends: list[str] = field(default_factory=list)
    debug: bool = False
    min_duration_seconds: int = 0
    summary_max_length: int = 200
    summary_truncate_suffix: str = "..."


def load_runtime_config() -> RuntimeConfig:
    """Load configuration from environment variables."""
    debug = os.environ.get("CCBELL_DEBUG", "") == "1"

    raw_backends = os.environ.get("CCBELL_BACKENDS", "")
    backends = [b.strip() for b in raw_backends.split(",") if b.strip()]

    def _safe_int(key: str, default: int) -> int:
        try:
            return int(os.environ.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    return RuntimeConfig(
        device_name=os.environ.get("CCBELL_DEVICE_NAME") or socket.gethostname(),
        backends=backends,
        debug=debug,
        min_duration_seconds=_safe_int("CCBELL_MIN_DURATION_SECONDS", 0),
        summary_max_length=_safe_int("CCBELL_SUMMARY_MAX_LENGTH", 200),
        summary_truncate_suffix=os.environ.get("CCBELL_SUMMARY_TRUNCATE_SUFFIX", "..."),
    )
