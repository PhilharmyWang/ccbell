#!/usr/bin/env python3
"""scripts/check_secrets.py — Scan repo for accidentally committed secrets.

Exit 0 if clean, exit 1 if suspicious patterns found.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Patterns that must NEVER appear in committed files
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Bark key (22-char standalone alphanumeric)",
     re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{22}(?![A-Za-z0-9])")),
    ("z.ai token (32hex.16alnum)",
     re.compile(r"[a-f0-9]{32}\.[A-Za-z0-9]{16}")),
    ("Chinese device keyword",
     re.compile(r"Windows\u672c\u5730|\u6d6a\u6f6e|\u6606\u660e|\u52a8\u7269\u6240")),
    ("Email address",
     re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("Private IPv4",
     re.compile(
         r"(?:"
         r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
         r"|192\.168\.\d{1,3}\.\d{1,3}"
         r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
         r")"
     )),
]

# Directories to skip
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache",
             "ccbell.egg-info", "dist", "build"}

# File suffixes to skip
SKIP_SUFFIXES = {".bak", ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico"}

# Files exempt from scanning (relative to repo root)
WHITELIST_FILES: set[str] = {
    "tests/test_check_secrets.py",
    "tests/test_notify.py",      # intentional test IPs / paths
    "config.yaml",               # .gitignored, user-specific
    "config.local.yaml",         # .gitignored, user-specific
}

# Line content that is always safe
CONTENT_WHITELIST = [
    "YOUR_BARK_KEY_HERE",
    "FAKE_KEY_",
    "example@example.com",
    "placeholder",
    "xxx@xxx.com",
    "xxxxxxxxxxxxxxxxxxxxxx",    # README example placeholder
    "192.168.1.10",              # common test fixture IP
]


def should_skip_file(path: Path, root: Path) -> bool:
    """Check if file should be skipped."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    parts = rel.parts
    for p in parts:
        if p in SKIP_DIRS:
            return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return False


def check_file(path: Path, root: Path) -> list[tuple[str, int, str, str]]:
    """Return list of (pattern_name, line_number, line, match) for violations."""
    violations: list[tuple[str, int, str, str]] = []

    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return violations

    if rel in WHITELIST_FILES:
        return violations

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations

    for line_no, line in enumerate(content.splitlines(), 1):
        # Skip whitelisted content
        if any(w in line for w in CONTENT_WHITELIST):
            continue
        for name, pattern in PATTERNS:
            for m in pattern.finditer(line):
                match_text = m.group(0)
                # Skip obvious non-secrets
                if name.startswith("Bark") and match_text in (
                    "rawgithubusercontentccbe",
                ):
                    continue
                violations.append((name, line_no, line.strip(), match_text))

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan repo for secrets")
    parser.add_argument("--root", default=None,
                        help="Root directory to scan (default: repo root)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent

    all_violations: list[tuple[str, str, int, str, str]] = []

    for dirpath, dirs, files in os.walk(root):
        # Prune skip dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            fpath = Path(dirpath) / fname
            if should_skip_file(fpath, root):
                continue
            violations = check_file(fpath, root)
            if violations:
                try:
                    rel = str(fpath.relative_to(root)).replace("\\", "/")
                except ValueError:
                    rel = str(fpath)
                for name, line_no, line, match in violations:
                    all_violations.append((rel, name, line_no, line, match))

    if all_violations:
        print(f"Found {len(all_violations)} potential secret(s):\n")
        for rel, name, line_no, line, match in all_violations:
            print(f"  {rel}:{line_no} [{name}]")
            print(f"    -> {match}")
            print(f"    line: {line[:120]}")
        print(
            "\nIf these are false positives, add them to the whitelist in scripts/check_secrets.py"
        )
        sys.exit(1)

    print("No secrets detected — repo is clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
