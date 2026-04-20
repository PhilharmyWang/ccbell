"""tests/test_check_secrets — tests for scripts/check_secrets.py."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CHECK = SCRIPTS / "check_secrets.py"
PY = sys.executable


def _run_check(root):
    """Run check_secrets.py against a given root directory."""
    result = subprocess.run(
        [PY, str(CHECK), "--root", str(root)],
        capture_output=True, text=True,
    )
    return result


# ── 1. Temp file with secret triggers exit 1 ─────────────────────────────────


def test_detects_secret():
    """A file containing a 32-hex + 16-alnum token triggers exit 1."""
    with tempfile.TemporaryDirectory() as tmp:
        secret_file = Path(tmp) / "leak.txt"
        # 32 hex chars + dot + 16 alnum chars = z.ai token pattern
        secret_file.write_text("token = abcdef1234567890abcdef1234567890ab.ABCDEFGHabcdefgh", encoding="utf-8")
        result = _run_check(tmp)
        assert result.returncode == 1, f"Expected exit 1 but got 0. stdout: {result.stdout}"
        assert "z.ai token" in result.stdout


# ── 2. Current repo scans clean ──────────────────────────────────────────────


def test_repo_is_clean():
    """Scanning the current repo should exit 0 (no secrets)."""
    repo_root = Path(__file__).resolve().parent.parent
    result = _run_check(repo_root)
    assert result.returncode == 0, (
        f"check_secrets.py found secrets in the repo!\n{result.stdout}"
    )
