#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed."
  echo "Install uv first:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [ ! -f .env ]; then
  printf 'MONITOR_TOKEN=abc123\nMONITOR_PORTS=8765,6006,8000,8888\n' > .env
  chmod 600 .env
  echo "Created .env with MONITOR_TOKEN and MONITOR_PORTS."
fi

uv sync

echo "Install complete."
echo "Next:"
echo "  uv run uvicorn backend.web:app --host 0.0.0.0 --port 8765"
