# RunWatch Release Usage

RunWatch is a local or LAN runtime status dashboard for tmux panes, ports,
Codex quota, and machine resources.

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

`install.sh` creates this file automatically. If you need stronger protection,
replace `abc123` with your own token:

```dotenv
MONITOR_TOKEN=abc123
MONITOR_PORTS=8765,6006,8000,8888
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

## Port Panel

The dashboard reads monitored ports from `.env`:

```text
8765, 6006, 8000, 8888
```

The panel is read-only. It shows whether a port is occupied plus the listener
command, PID, user, and address when available. If a listener is hidden from
`lsof` but the port cannot be bound, the panel marks it as `unavailable`. If
the port cannot be inspected at all, it is marked as `unknown`.

## Resource Panel

The dashboard also shows read-only system resources:

- CPU load from `/proc/loadavg`
- Memory usage from `/proc/meminfo`
- GPU utilization, memory, and temperature from `nvidia-smi` when available

If `nvidia-smi` is missing or fails, the GPU card is marked as `unknown`.

## Implementation Flow

- `backend/ports.py` collects port listeners with `lsof`.
- `backend/resources.py` collects CPU, memory, and GPU resource data.
- `backend/web.py` adds port data to `/api/status`.
- `backend/static/index.html` renders resource and port cards.
- `backend/test_ports.py` covers parser and collector behavior.
- `backend/test_resources.py` covers resource parser and collector behavior.
- `backend/test_web.py` checks that `/api/status` includes `ports`.

## Security Notes

- Use this on a trusted LAN only.
- Keep `.env` private. It contains `MONITOR_TOKEN`.
- The web UI shows recent tmux output, working directories, listener PIDs, and local Codex quota.
