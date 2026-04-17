# ccbell

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Push a notification to your iPhone when Claude Code finishes or needs your input.

## Install

```bash
cd /path/to/ccbell
pip install -e .
```

Or just clone and set `PYTHONPATH` — no third-party dependencies.

## Setup

**1. Get a Bark key** from the [Bark](https://github.com/Finb/bark-server) iOS app.

**2. Set environment variables** (add to `~/.bashrc` / `~/.zshrc` / PowerShell profile):

```bash
export BARK_KEY="your-bark-key-here"
export CCBELL_DEVICE_NAME="laptop"
export CCBELL_DEVICE_EMOJI="💻"     # optional
```

**3. Register hooks** in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python /path/to/ccbell/hooks/dispatch.py"
      }
    ],
    "Notification": [
      {
        "type": "command",
        "command": "python /path/to/ccbell/hooks/dispatch.py"
      }
    ],
    "SubagentStop": [
      {
        "type": "command",
        "command": "python /path/to/ccbell/hooks/dispatch.py"
      }
    ]
  }
}
```

Replace `/path/to/ccbell` with your actual path.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BARK_KEY` | *(required)* | Bark device key |
| `BARK_SERVER` | `https://api.day.app` | Bark server URL |
| `CCBELL_DEVICE_NAME` | hostname | Shown in notification title |
| `CCBELL_DEVICE_EMOJI` | `💻` | Device emoji |
| `CCBELL_GROUP` | `ccbell-{DEVICE_NAME}` | Bark notification group |
| `CCBELL_DEBUG` | `0` | Set to `1` for verbose logging |
| `CCBELL_DRY_RUN` | `0` | Set to `1` to print without pushing |
| `CCBELL_MIN_DURATION_SECONDS` | `0` | Skip sessions shorter than this |
| `CCBELL_SUMMARY_MAX_LENGTH` | `200` | Max summary characters |

## License

[MIT](LICENSE)
