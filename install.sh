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
  printf 'MONITOR_TOKEN=abc123\n' > .env
  chmod 600 .env
  echo "Created .env with MONITOR_TOKEN=abc123."
fi

UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync

echo "Install complete."
echo "Next:"
echo "  UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn backend.web:app --host 0.0.0.0 --port 8765"
