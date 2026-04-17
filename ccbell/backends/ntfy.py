"""
ccbell.backends.ntfy — ntfy push notification backend.

Sends a push notification via the ntfy HTTP API (POST) using only urllib.

Input:  CCBELL_TITLE, CCBELL_BODY, CCBELL_GROUP, CCBELL_LEVEL, CCBELL_BACKEND_CONFIG
Output: exit 0 on success, non-0 on failure
Usage:
    # via dispatcher (subprocess):
    #   auto-invoked with env vars
    # standalone:
    export CCBELL_TITLE="Test" CCBELL_BODY="Hello" CCBELL_GROUP="ccbell" CCBELL_LEVEL="info"
    export CCBELL_BACKEND_CONFIG='{"server":"https://ntfy.sh","topic":"ccbell-YOUR-TOPIC"}'
    python -m ccbell.backends.ntfy
Created: 2026-04-17
"""

from __future__ import annotations

import sys
import urllib.parse
import urllib.request
from urllib.error import URLError

from ccbell.backends.base import read_invocation_env

_DEFAULT_PRIORITY_MAP: dict[str, int] = {
    "info": 3,
    "warning": 4,
    "error": 5,
}


def _encode_header(value: str) -> str:
    """Encode a header value containing non-ASCII chars via percent-encoding."""
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        return urllib.parse.quote(value, safe="")


def main() -> int:
    """Send notification via ntfy API. Returns 0 on success."""
    env = read_invocation_env()
    cfg = env["backend_config"]

    server = cfg.get("server", "")
    topic = cfg.get("topic", "")
    token = cfg.get("token", "")
    raw_tags = cfg.get("tags", "")
    priority_map = cfg.get("priority_map", _DEFAULT_PRIORITY_MAP)

    if not server:
        print("ccbell backend error: ntfy server missing", file=sys.stderr)
        return 2
    if not topic:
        print("ccbell backend error: ntfy topic missing", file=sys.stderr)
        return 2

    # resolve priority
    mapped_priority = priority_map.get(env["level"], 3)
    if isinstance(mapped_priority, str):
        try:
            mapped_priority = int(mapped_priority)
        except (ValueError, TypeError):
            mapped_priority = 3

    # resolve tags
    if isinstance(raw_tags, list):
        tags_csv = ",".join(str(t) for t in raw_tags)
    elif raw_tags:
        tags_csv = str(raw_tags)
    else:
        tags_csv = ""

    # build headers
    title = env["title"]
    encoded_title = _encode_header(title)

    headers: dict[str, str] = {
        "Title": encoded_title,
        "Priority": str(mapped_priority),
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags_csv:
        headers["Tags"] = tags_csv
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # body: if title was non-ASCII, prepend original title line as fallback
    body_text = env["body"]
    if encoded_title != title:
        body_text = f"标题：{title}\n{body_text}"

    url = f"{server}/{topic}"
    data = body_text.encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if 200 <= resp.status < 300:
                print("ok")
                return 0
            else:
                print(f"ntfy HTTP {resp.status}", file=sys.stderr)
                return 1
    except (URLError, OSError) as exc:
        print(f"ntfy request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ntfy unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
