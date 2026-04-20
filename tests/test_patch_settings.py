"""tests/test_patch_settings — tests for scripts/_patch_settings.py."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PATCH = SCRIPTS / "_patch_settings.py"
PY = sys.executable


def _run(tmp_path, extra_args, env=None):
    """Run _patch_settings.py with a temp settings file."""
    settings = tmp_path / "settings.json"
    dispatch = tmp_path / "hooks" / "dispatch.py"
    dispatch.parent.mkdir(parents=True, exist_ok=True)
    dispatch.write_text("# dummy\n")

    args = [
        PY, str(PATCH),
        "--settings-path", str(settings),
        "--dispatch-path", str(dispatch),
        "--bark-key", "testkey1234567890abcd",
        "--device-name", "TestPC",
        "--device-emoji", "🧪",
    ] + extra_args

    result = subprocess.run(
        args, capture_output=True, encoding="utf-8", errors="replace", env=env,
    )
    return result, settings


# ── 1. Empty file upsert ─────────────────────────────────────────────────────


def test_upsert_from_empty(tmp_path):
    """Starting from no settings.json, creates one with hooks + env."""
    result, settings = _run(tmp_path, [])
    assert result.returncode == 0, result.stderr

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "hooks" in data
    for event in ("Stop", "Notification", "SubagentStop"):
        assert event in data["hooks"]
        matcher_list = data["hooks"][event]
        assert len(matcher_list) == 1
        assert matcher_list[0]["matcher"] == ""
        assert any("dispatch.py" in h["command"] for h in matcher_list[0]["hooks"])

    assert data["env"]["BARK_KEY"] == "testkey1234567890abcd"
    assert data["env"]["CCBELL_DEVICE_NAME"] == "TestPC"
    assert data["env"]["CCBELL_DEVICE_EMOJI"] == "🧪"


# ── 2. Old powershell hook gets cleaned ──────────────────────────────────────


def test_clean_old_powershell_hook(tmp_path):
    """Old powershell.exe / windows-notification.ps1 entries are removed."""
    settings = tmp_path / "settings.json"
    dispatch = tmp_path / "hooks" / "dispatch.py"
    dispatch.parent.mkdir(parents=True, exist_ok=True)
    dispatch.write_text("# dummy\n")

    old_data = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "powershell.exe -File windows-notification.ps1"},
                    ],
                }
            ],
        },
    }
    settings.write_text(json.dumps(old_data, indent=2), encoding="utf-8")

    result = subprocess.run(
        [PY, str(PATCH),
         "--settings-path", str(settings),
         "--dispatch-path", str(dispatch),
         "--bark-key", "testkey1234567890abcd",
         "--device-name", "TestPC",
         "--device-emoji", "🧪"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    data = json.loads(settings.read_text(encoding="utf-8"))
    stop_hooks = data["hooks"]["Stop"][0]["hooks"]
    commands = [h["command"] for h in stop_hooks]
    assert not any("powershell.exe" in c for c in commands)
    assert not any("windows-notification.ps1" in c for c in commands)
    assert any("dispatch.py" in c for c in commands)


# ── 3. Idempotent (no duplicates on repeated run) ────────────────────────────


def test_idempotent(tmp_path):
    """Running twice produces identical hooks (no duplicates)."""
    result1, settings = _run(tmp_path, [])
    assert result1.returncode == 0, result1.stderr
    data1 = json.loads(settings.read_text(encoding="utf-8"))

    result2, settings = _run(tmp_path, [])
    assert result2.returncode == 0, result2.stderr
    data2 = json.loads(settings.read_text(encoding="utf-8"))

    for event in ("Stop", "Notification", "SubagentStop"):
        hooks1 = data1["hooks"][event][0]["hooks"]
        hooks2 = data2["hooks"][event][0]["hooks"]
        assert hooks1 == hooks2, f"{event}: hooks changed on second run"

    # Also verify only one dispatch.py entry per event
    for event in ("Stop", "Notification", "SubagentStop"):
        dispatch_entries = [
            h for h in data2["hooks"][event][0]["hooks"]
            if "dispatch.py" in h.get("command", "")
        ]
        assert len(dispatch_entries) == 1, f"{event}: duplicate dispatch entries"


# ── 4. Masked log does not contain full key ──────────────────────────────────


def test_masked_log(tmp_path):
    """BARK_KEY and ANTHROPIC_AUTH_TOKEN are masked in output."""
    result, _ = _run(tmp_path, ["--zai-token", "abcdef1234567890abcdef1234567890ab"])
    assert result.returncode == 0

    output = result.stdout
    # Full key should NOT appear in output
    assert "testkey1234567890abcd" not in output
    assert "abcdef1234567890abcdef1234567890ab" not in output
    # Masked version should appear (first4 + stars + last4)
    assert re.search(r"test\*+abcd", output)


# ── 5. Dry-run does not write to disk or create backup ───────────────────────


def test_dry_run_no_write(tmp_path):
    """--dry-run: no file written, no backup created."""
    settings = tmp_path / "settings.json"
    dispatch = tmp_path / "hooks" / "dispatch.py"
    dispatch.parent.mkdir(parents=True, exist_ok=True)
    dispatch.write_text("# dummy\n")

    # Write initial content
    initial = '{"existing": true}'
    settings.write_text(initial, encoding="utf-8")

    result = subprocess.run(
        [PY, str(PATCH),
         "--settings-path", str(settings),
         "--dispatch-path", str(dispatch),
         "--bark-key", "testkey1234567890abcd",
         "--device-name", "TestPC",
         "--device-emoji", "🧪",
         "--dry-run"],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0

    # Original file unchanged
    assert settings.read_text(encoding="utf-8") == initial

    # No backup files created
    bak_files = list(tmp_path.glob("*.bak-*"))
    assert len(bak_files) == 0, f"Unexpected backup files: {bak_files}"
