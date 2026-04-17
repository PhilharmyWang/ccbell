"""
ccbell.backends.bark — Bark push notification backend.

Sends a push notification via the Bark HTTP API using only urllib (no requests).

Input:  CCBELL_TITLE, CCBELL_BODY, CCBELL_GROUP, CCBELL_LEVEL, CCBELL_BACKEND_CONFIG
Output: exit 0 on success, non-0 on failure
Usage:
    # via dispatcher (subprocess):
    #   auto-invoked with env vars
    # standalone:
    export CCBELL_TITLE="Test" CCBELL_BODY="Hello" CCBELL_GROUP="ccbell" CCBELL_LEVEL="info"
    export CCBELL_BACKEND_CONFIG='{"server":"https://api.day.app","key":"YOUR_BARK_KEY"}'
    python -m ccbell.backends.bark
Created: 2026-04-17
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from urllib.error import URLError

from ccbell.backends.base import die, read_invocation_env


def _url_encode(text: str) -> str:
    """Percent-encode text for URL path segments (safe="")."""
    return urllib.parse.quote(text, safe="")


def main() -> int:
    """Send notification via Bark API. Returns 0 on success."""
    env = read_invocation_env()
    cfg = env["backend_config"]

    server = cfg.get("server", "https://api.day.app")
    key = cfg.get("key", "")
    sound = cfg.get("sound", "")
    level_map = cfg.get("level_map", {})

    if not key:
        print("ccbell backend error: Bark key missing", file=sys.stderr)
        return 2

    # resolve level
    mapped_level = level_map.get(env["level"], "active")

    # build URL
    encoded_title = _url_encode(env["title"])
    encoded_body = _url_encode(env["body"])
    encoded_group = _url_encode(env["group"])

    url = f"{server}/{key}/{encoded_title}/{encoded_body}"
    params = {"group": encoded_group, "level": mapped_level}
    if sound:
        params["sound"] = sound
    url += "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if 200 <= resp.status < 300:
                print("ok")
                return 0
            else:
                print(f"Bark HTTP {resp.status}", file=sys.stderr)
                return 1
    except (URLError, OSError) as exc:
        print(f"Bark request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Bark unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
