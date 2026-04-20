# ccbell

> Bring Claude Code completion notifications to your iPhone. Works across Windows / macOS / Linux.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Tests](https://github.com/PhilharmyWang/ccbell/actions/workflows/test.yml/badge.svg)](.github/workflows/test.yml)

## Features

- **Multi-device distinction** — each machine gets its own name + emoji, Bark notifications are grouped by device
- **stop_reason emoji** — end_turn / error / interrupted / max_tokens each get a distinct emoji and priority
- **Path sanitization** — user home paths and private IPs are redacted in push body
- **Zero third-party deps** — pure Python 3.9+ stdlib, no pip install needed
- **One-line install** — single PowerShell or Bash command with your Bark key

## Screenshots

> TODO — add a screenshot at `docs/screenshot.png`

## Prerequisites

1. iPhone / iPad with [Bark](https://apps.apple.com/app/bark-customed-notifications/id1403753865) installed
2. Open Bark, copy your Key (looks like `xxxxxxxxxxxxxxxxxxxxxx`)
3. Python >= 3.9 on this machine
4. [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed

## Quick Start (3 steps)

### Windows

**1. Download the install script**

```powershell
iwr https://raw.githubusercontent.com/PhilharmyWang/ccbell/main/scripts/install.ps1 -OutFile $env:TEMP\ccbell-install.ps1
```

**2. Run it (replace with your Bark Key, device name, emoji)**

```powershell
powershell -ExecutionPolicy Bypass -File $env:TEMP\ccbell-install.ps1 `
  -BarkKey "YOUR_BARK_KEY_HERE" `
  -DeviceName "MyLaptop" `
  -DeviceEmoji "💻"
```

**3. Open a new Claude Code session, say "hi" — your iPhone should get a notification**

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/PhilharmyWang/ccbell/main/scripts/install.sh | bash -s -- \
  --bark-key "YOUR_BARK_KEY_HERE" \
  --device-name "MyServer" \
  --device-emoji "🖥️"
```

### Air-gapped server (offline)

Clone on a machine with internet, `scp` to the target, then:

```bash
bash ~/ccbell/scripts/install.sh --offline \
  --bark-key "YOUR_BARK_KEY_HERE" \
  --device-name "HPC-Node" \
  --device-emoji "🖧"
```

## Multi-device Deployment

Use different `--device-name` and `--device-emoji` per machine. Bark groups notifications by device.

| Device | name | emoji |
|--------|------|-------|
| Laptop | Laptop | 💻 |
| Desktop | Desktop | 🖥️ |
| HPC node | HPC-Node | 🖧 |

## How It Works

```
flowchart LR
    CC[Claude Code session] -->|Stop hook| D[hooks/dispatch.py]
    D --> N[ccbell/notify.py]
    N -->|HTTPS| B[Bark API]
    B --> P[iPhone]
```

Claude Code's **Stop / Notification / SubagentStop** events pipe a JSON payload to `dispatch.py`. The `notify` module extracts a summary, sanitizes paths, picks an emoji, then POSTs to Bark.

## Environment Variables

All optional overrides — the install script writes the first three to Claude Code's `settings.json` `env` block so child processes inherit them automatically.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BARK_KEY` | yes | — | Your Bark key |
| `BARK_SERVER` | | `https://api.day.app` | Custom Bark server URL |
| `CCBELL_DEVICE_NAME` | yes | hostname | Device identifier |
| `CCBELL_DEVICE_EMOJI` | | 💻 | Title prefix emoji |
| `CCBELL_GROUP` | | `ccbell-<device_name>` | Bark group |
| `CCBELL_DEBUG` | | — | Set `1` to enable debug logging |
| `CCBELL_DRY_RUN` | | — | Set `1` to log without pushing |
| `CCBELL_MIN_DURATION_SECONDS` | | 0 | Skip notifications for short sessions |
| `CCBELL_SUMMARY_MAX_LENGTH` | | 300 | Max chars for summary truncation |

## stop_reason Emoji Map

| Event | stop_reason | Emoji | Bark Level |
|-------|-------------|-------|------------|
| Stop | end_turn | ✅ 完成 | active |
| Stop | error / api_error | ❌ 出错退出 | timeSensitive |
| Stop | user_interrupted | 🛑 已中断 | active |
| Stop | max_tokens | ⚠️ 超长截断 | timeSensitive |
| Notification | — | ⚠️ 需要确认 | timeSensitive |
| SubagentStop | — | 🤖 子任务完成 | active |

## FAQ

**Q: Where do I find my Bark Key?**
A: Open the Bark app on your iPhone — the key is on the home screen. Tap to copy.

**Q: No notification after installing?**
A: (1) Confirm `settings.json` has the three ccbell hooks. (2) Close old Claude Code sessions and open a new one. (3) Manual smoke test: `cat tests/fixtures/sample_stop.json | python hooks/dispatch.py`.

**Q: Device name with non-ASCII characters causes errors?**
A: Fixed in v0.2.0 — URL params use `urlencode()`. Make sure you're on the latest version.

**Q: How to use a self-hosted Bark server?**
A: Pass `--bark-server https://your.server/` to the install script.

**Q: How to uninstall?**
A: Run `scripts/uninstall.ps1` (Windows) or `scripts/uninstall.sh` (macOS/Linux).

## Development

```bash
git clone https://github.com/PhilharmyWang/ccbell.git
cd ccbell
python -m pytest tests/ -v
```

Architecture: [docs/DESIGN.md](docs/DESIGN.md)

## License

[MIT](LICENSE)
