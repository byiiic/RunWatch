import json
import re
import select
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path


CODEX_HOME = Path.home() / ".codex"
CODEX_QUOTA_CACHE_SECONDS = 10
CODEX_APP_SERVER_TIMEOUT_SECONDS = 5


def _lines_in_reverse(path: Path, chunk_size: int = 8192):
    with path.open("rb") as handle:
        position = handle.seek(0, 2)
        remainder = b""

        while position > 0:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            chunk = handle.read(read_size) + remainder
            lines = chunk.split(b"\n")
            remainder = lines[0]

            for line in reversed(lines[1:]):
                if line:
                    yield line.decode("utf-8", errors="ignore")

        if remainder:
            yield remainder.decode("utf-8", errors="ignore")


def _timestamp_key(value) -> float:
    if not isinstance(value, str):
        return float("-inf")

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return float("-inf")


def _snake_case(value):
    if isinstance(value, dict):
        return {
            re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower(): _snake_case(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_snake_case(item) for item in value]
    return value


def _normalize_rate_limits(rate_limits: dict) -> dict:
    normalized = _snake_case(rate_limits)
    for name in ("primary", "secondary"):
        window = normalized.get(name)
        if window and "window_duration_mins" in window:
            window["window_minutes"] = window.pop("window_duration_mins")
    return normalized


def _send_app_server_message(process, message: dict):
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin is unavailable")

    process.stdin.write((json.dumps(message) + "\n").encode())
    process.stdin.flush()


def _read_app_server_response(process, request_id: int, deadline: float) -> dict:
    if process.stdout is None:
        raise RuntimeError("Codex app-server stdout is unavailable")

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex app-server request timed out")

        readable, _, _ = select.select([process.stdout], [], [], remaining)
        if not readable:
            raise TimeoutError("Codex app-server request timed out")

        line = process.stdout.readline()
        if not line:
            raise RuntimeError("Codex app-server exited before replying")

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise RuntimeError(f"Codex app-server error: {message['error']}")
        return message.get("result", {})


def query_codex_quota(
    command=("codex", "app-server", "--stdio"),
    timeout_seconds: float = CODEX_APP_SERVER_TIMEOUT_SECONDS,
) -> dict:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )
    deadline = time.monotonic() + timeout_seconds

    try:
        _send_app_server_message(
            process,
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "runwatch", "version": "0.1.0"},
                },
            },
        )
        _read_app_server_response(process, 1, deadline)
        _send_app_server_message(process, {"method": "initialized"})
        _send_app_server_message(
            process,
            {"id": 2, "method": "account/rateLimits/read"},
        )
        result = _read_app_server_response(process, 2, deadline)
        rate_limits = result.get("rateLimits")
        if not rate_limits:
            raise RuntimeError("Codex app-server returned no rate limits")

        return {
            "available": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rate_limits": _normalize_rate_limits(rate_limits),
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class CodexQuotaCache:
    def __init__(
        self,
        reader: Callable[[], dict] = None,
        ttl_seconds: int = CODEX_QUOTA_CACHE_SECONDS,
        clock: Callable[[], float] = time.time,
    ):
        self.reader = reader or read_codex_quota
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.cached_value = None
        self.cached_at = None

    def get(self) -> dict:
        now = self.clock()
        if (
            self.cached_value is not None
            and self.cached_at is not None
            and now - self.cached_at < self.ttl_seconds
        ):
            return self.cached_value

        self.cached_value = self.reader()
        self.cached_at = now
        return self.cached_value


def find_latest_codex_quota(codex_home: Path = CODEX_HOME) -> dict:
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        return {
            "available": False,
            "reason": "no local Codex sessions directory found",
        }

    session_files = sorted(
        sessions_dir.rglob("*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    latest_event = None
    latest_timestamp_key = float("-inf")

    for path in session_files:
        try:
            for line in _lines_in_reverse(path):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                payload = event.get("payload", {})
                rate_limits = payload.get("rate_limits") or event.get("rate_limits")
                if not rate_limits:
                    continue

                timestamp = event.get("timestamp")
                timestamp_key = _timestamp_key(timestamp)
                if latest_event is None or timestamp_key > latest_timestamp_key:
                    latest_event = {
                        "available": True,
                        "timestamp": timestamp,
                        "rate_limits": rate_limits,
                    }
                    latest_timestamp_key = timestamp_key
                break
        except OSError:
            continue

    if latest_event is not None:
        return latest_event

    return {
        "available": False,
        "reason": "no local Codex rate limit snapshot found",
    }


def read_codex_quota() -> dict:
    try:
        return query_codex_quota()
    except (OSError, RuntimeError, TimeoutError):
        return find_latest_codex_quota()
