# Monitor Release Usage

This package is for local or LAN tmux monitoring.

## Requirements

- Linux
- tmux
- uv
- Python 3.10 or newer

Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install

```bash
bash install.sh
```

This creates `.env` with a local `MONITOR_TOKEN` and installs dependencies with `uv sync`.

## .env Example

`install.sh` creates this file automatically. If you create it manually, use your
own random value:

```dotenv
MONITOR_TOKEN=abc123
```

Do not commit `.env`.

## Start

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn backend.web:app --host 0.0.0.0 --port 8765
```

Open `http://127.0.0.1:8765/` locally, or use the machine LAN IP from another
device on the same trusted network. Enter the token from `.env` when prompted.
The token is sent as an `Authorization` header and is not placed in the URL.
Uvicorn logs stay in the terminal so the tmux pane remains visibly active.

## Stop

```bash
Ctrl+C
```

## Change Host Or Port

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn backend.web:app --host 0.0.0.0 --port 8766
```

## Security Notes

- Use this on a trusted LAN only.
- Keep `.env` private. It contains `MONITOR_TOKEN`.
- The web UI shows recent tmux output, working directories, and local Codex quota.
