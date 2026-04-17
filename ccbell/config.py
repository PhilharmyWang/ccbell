"""
ccbell.config — runtime configuration from YAML and environment variables.

Looks for config.yaml in multiple locations (CCBELL_CONFIG env, cwd, ~/.ccbell/,
repo root). Falls back to pure env-var defaults for backward compatibility.

Input:  config.yaml file + CCBELL_* environment variables
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
from pathlib import Path

# Lazy import: yaml is a hard dependency (declared in pyproject.toml)
# but we guard the import to give a clear error message.
try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DeviceConfig:
    name: str = ""
    group: str = "local"


@dataclass
class BackendConfig:
    name: str = ""
    enabled: bool = True
    params: dict = field(default_factory=dict)


@dataclass
class EnricherConfig:
    name: str = ""
    enabled: bool = True
    params: dict = field(default_factory=dict)


@dataclass
class FilterConfig:
    min_duration_seconds: int = 0


@dataclass
class SummaryConfig:
    max_length: int = 200
    truncate_suffix: str = "..."


@dataclass
class RuntimeConfig:
    device: DeviceConfig = field(default_factory=DeviceConfig)
    backends: list[BackendConfig] = field(default_factory=list)
    enrichers: list[EnricherConfig] = field(default_factory=list)
    filters: FilterConfig = field(default_factory=FilterConfig)
    summary: SummaryConfig = field(default_factory=SummaryConfig)
    debug: bool = False
    source_path: str = ""

    # --- backward-compatible convenience properties (Step 1/2 callers) ---
    @property
    def device_name(self) -> str:
        return self.device.name

    @property
    def min_duration_seconds(self) -> int:
        return self.filters.min_duration_seconds

    @property
    def summary_max_length(self) -> int:
        return self.summary.max_length

    @property
    def summary_truncate_suffix(self) -> str:
        return self.summary.truncate_suffix


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

_CANDIDATE_PATHS = [
    lambda: os.environ.get("CCBELL_CONFIG", ""),
    lambda: str(Path.cwd() / "config.yaml"),
    lambda: str(Path.home() / ".ccbell" / "config.yaml"),
]


def _find_config() -> tuple[dict | None, str]:
    """Try to find and parse a config.yaml. Returns (data, path)."""
    if yaml is None:
        return None, ""

    for fn in _CANDIDATE_PATHS:
        p = fn()
        if p and Path(p).is_file():
            try:
                data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data, str(p)
            except Exception:
                pass
            break  # file exists but failed to parse → stop searching
    return None, ""


def _parse_backends(raw: list) -> list[BackendConfig]:
    result: list[BackendConfig] = []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not name:
            continue
        # everything except name/enabled goes into params
        params = {k: v for k, v in item.items() if k not in ("name", "enabled")}
        result.append(BackendConfig(
            name=name,
            enabled=bool(item.get("enabled", True)),
            params=params,
        ))
    return result


def _parse_enrichers(raw: list) -> list[EnricherConfig]:
    result: list[EnricherConfig] = []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not name:
            continue
        params = {k: v for k, v in item.items() if k not in ("name", "enabled")}
        result.append(EnricherConfig(
            name=name,
            enabled=bool(item.get("enabled", True)),
            params=params,
        ))
    return result


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_runtime_config() -> RuntimeConfig:
    """Load configuration from YAML (if found) + environment variable overrides."""
    data, source_path = _find_config()

    # defaults
    device = DeviceConfig(name=socket.gethostname(), group="local")
    backends: list[BackendConfig] = []
    enrichers: list[EnricherConfig] = []
    filters = FilterConfig()
    summary = SummaryConfig()

    if data:
        # device
        d = data.get("device")
        if isinstance(d, dict):
            device.name = d.get("name", device.name)
            device.group = d.get("group", device.group)

        # backends
        backends = _parse_backends(data.get("backends", []))

        # enrichers
        enrichers = _parse_enrichers(data.get("enrichers", []))

        # filters
        f = data.get("filters")
        if isinstance(f, dict):
            filters.min_duration_seconds = _safe_int(
                f.get("min_duration_seconds", 0), 0
            )

        # summary
        s = data.get("summary")
        if isinstance(s, dict):
            summary.max_length = _safe_int(s.get("max_length", 200), 200)
            summary.truncate_suffix = str(s.get("truncate_suffix", "..."))

    # env overrides (env takes precedence over YAML)
    env_device = os.environ.get("CCBELL_DEVICE_NAME")
    if env_device:
        device.name = env_device

    debug = os.environ.get("CCBELL_DEBUG", "") == "1"

    return RuntimeConfig(
        device=device,
        backends=backends,
        enrichers=enrichers,
        filters=filters,
        summary=summary,
        debug=debug,
        source_path=source_path,
    )
