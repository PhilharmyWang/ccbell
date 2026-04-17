# ccbell

<!-- badges placeholder -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Stars](https://img.shields.io/github/stars/<your-gh-user>/ccbell?style=social)

**A multi-device notification hub for Claude Code sessions.**

## What is ccbell?

ccbell is a lightweight notification daemon designed for ML researchers, scientific computing users, and developers working on remote SSH sessions or HPC clusters. It automatically pushes a concise summary — device name, project name, session ID, and the last assistant reply — to your phone or IM whenever a Claude Code session ends or waits for user input.

Optionally, ccbell can enrich notifications with training experiment links, job scheduler status, GPU utilization, and Git branch information through a pluggable enricher system.

## Features

- **Multi-device grouping** — Instantly tell which notification came from your laptop, workstation, or remote cluster
- **Session-aware summaries** — Automatically parses Claude Code `transcript.jsonl` to extract the last assistant reply
- **Pluggable enrichers** — Optionally attach training platform links (W&B, SwanLab), Slurm job status, GPU stats, Git branch, and more
- **Long-task threshold filter** — Short sessions are silently skipped; only long-running tasks trigger a push
- **Multi-backend pluggable notifications** — Bark, ntfy, Feishu, WeCom, Telegram, Email; easy to add your own
- **Zero-friction setup** — Configure once via `config.yaml`, hooks are auto-registered
- **Privacy-first** — Sensitive paths are scrubbed, summaries are truncated, config stays local
- **Silent failure** — Notification errors never interrupt your Claude Code workflow

## Supported platforms

- Windows
- macOS
- Linux
- Remote SSH sessions
- HPC clusters (Slurm, PBS, etc.)

## Supported backends

| Backend   | Protocol | Notes                        |
|-----------|----------|------------------------------|
| [Bark](https://github.com/Finb/bark-server) | HTTP     | iOS push, self-hosted        |
| [ntfy](https://ntfy.sh)   | HTTP     | Cross-platform, self-hosted  |
| Feishu    | Webhook  | Feishu / Lark group bot      |
| WeCom     | Webhook  | WeCom group bot              |
| Telegram  | Bot API  | Via Telegram Bot             |
| Email     | SMTP     | Any email provider           |

## Quick start

> **Note:** ccbell is currently at v0.1 dev. No real push notifications are sent yet — this is a dry-run skeleton to validate the hook integration.

### 1. Register hooks in Claude Code settings

Add the following to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python3 /path/to/ccbell/hooks/dispatch.py"
      }
    ],
    "Notification": [
      {
        "type": "command",
        "command": "python3 /path/to/ccbell/hooks/dispatch.py"
      }
    ]
  }
}
```

Replace `/path/to/ccbell` with the actual path to your local ccbell repository.

### 2. Dry-run test

```bash
# From the ccbell repository root
echo '{"hook_event_name":"Stop","session_id":"abcdef1234567890","cwd":"/tmp/demo-project","transcript_path":""}' \
  | CCBELL_DEVICE_NAME=laptop CCBELL_DEBUG=1 python3 hooks/dispatch.py
```

You should see structured output on stderr (CCBELL_TITLE, CCBELL_BODY, etc.) and the exit code should be `0`.
Logs are also written to `~/.ccbell/ccbell.log`.

## Configuration

> **TODO** — `config.yaml` reference and examples will be added in a future release.

## Enrichers

> **TODO** — Enricher usage and custom enricher development guide will be added in a future release.

## FAQ

> **TODO** — Frequently asked questions will be added in a future release.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

> **TODO** — Contribution guidelines will be added in a future release.

## License

This project is licensed under the [MIT License](LICENSE).
