#!/usr/bin/env bash
# scripts/install.sh — ccbell installer for Linux/macOS.
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
BARK_KEY=""
DEVICE_NAME=""
DEVICE_EMOJI=""
INSTALL_DIR="$HOME/tools/ccbell"
REPO="https://github.com/PhilharmyWang/ccbell.git"
OFFLINE=false
ZAI_TOKEN=""
BARK_SERVER=""

usage() {
    cat <<'USAGE'
Usage:
  bash install.sh \
    --bark-key KEY \
    --device-name NAME \
    --device-emoji EMOJI \
    [--install-dir DIR] [--repo URL] [--offline] \
    [--zai-token TOKEN] [--bark-server URL]

Required: --bark-key, --device-name, --device-emoji
USAGE
    exit 1
}

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bark-key)      BARK_KEY="$2";      shift 2 ;;
        --device-name)   DEVICE_NAME="$2";   shift 2 ;;
        --device-emoji)  DEVICE_EMOJI="$2";  shift 2 ;;
        --install-dir)   INSTALL_DIR="$2";   shift 2 ;;
        --repo)          REPO="$2";          shift 2 ;;
        --offline)       OFFLINE=true;       shift   ;;
        --zai-token)     ZAI_TOKEN="$2";     shift 2 ;;
        --bark-server)   BARK_SERVER="$2";   shift 2 ;;
        *)               echo "Unknown option: $1"; usage ;;
    esac
done

# ── 1. Validate required ─────────────────────────────────────────────────────
[[ -z "$BARK_KEY" ]]      && { echo "ERROR: --bark-key is required";      usage; }
[[ -z "$DEVICE_NAME" ]]   && { echo "ERROR: --device-name is required";   usage; }
[[ -z "$DEVICE_EMOJI" ]]  && { echo "ERROR: --device-emoji is required";  usage; }

# ── 2. Python >= 3.9 ─────────────────────────────────────────────────────────
PY="python3"
if ! command -v python3 &>/dev/null; then
    PY="python"
fi

PY_VER=$($PY --version 2>&1 || true)
if [[ ! "$PY_VER" =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
    echo "ERROR: Python not found. Install Python >= 3.9."
    exit 1
fi
MAJOR=${BASH_REMATCH[1]}
MINOR=${BASH_REMATCH[2]}
if [[ "$MAJOR" -lt 3 ]] || { [[ "$MAJOR" -eq 3 ]] && [[ "$MINOR" -lt 9 ]]; }; then
    echo "ERROR: Python >= 3.9 required, found $PY_VER"
    exit 1
fi
echo "Python: $PY_VER OK"

# ── 3. Clone / pull or offline ───────────────────────────────────────────────
if [[ "$OFFLINE" == true ]]; then
    INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    echo "Offline mode, using repo at: $INSTALL_DIR"
else
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        echo "Updating existing clone..."
        git -C "$INSTALL_DIR" pull
    else
        echo "Cloning $REPO ..."
        git clone "$REPO" "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

# ── 4. pytest ────────────────────────────────────────────────────────────────
echo ""
echo "Running tests..."
$PY -m pytest -q
echo "Tests passed OK"

# ── 5. Patch settings.json ───────────────────────────────────────────────────
DISPATCH_PATH="$INSTALL_DIR/hooks/dispatch.py"
PATCH_SCRIPT="$INSTALL_DIR/scripts/_patch_settings.py"

PATCH_ARGS=(
    "$PATCH_SCRIPT"
    "--dispatch-path" "$DISPATCH_PATH"
    "--python-bin"    "$PY"
    "--bark-key"      "$BARK_KEY"
    "--device-name"   "$DEVICE_NAME"
    "--device-emoji"  "$DEVICE_EMOJI"
)
[[ -n "$ZAI_TOKEN" ]]    && PATCH_ARGS+=("--zai-token"    "$ZAI_TOKEN")
[[ -n "$BARK_SERVER" ]]  && PATCH_ARGS+=("--bark-server"  "$BARK_SERVER")

$PY "${PATCH_ARGS[@]}"

# ── Connectivity check (warn only) ───────────────────────────────────────────
if [[ "$OFFLINE" == false ]]; then
    if ! curl -sf --max-time 5 https://api.day.app >/dev/null 2>&1; then
        echo "WARNING: cannot reach api.day.app (Bark server). Check network/firewall."
    fi
fi

# ── 6. Smoke test ────────────────────────────────────────────────────────────
echo ""
echo "Smoke test..."
cat tests/fixtures/sample_stop.json | $PY hooks/dispatch.py
echo "Smoke test passed OK"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Done! 新开一个 Claude Code 会话并说一句话，iPhone 应收到通知。"
