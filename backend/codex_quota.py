import json
import time
from collections.abc import Callable
from pathlib import Path


CODEX_HOME = Path.home() / ".codex"
CODEX_QUOTA_CACHE_SECONDS = 120


class CodexQuotaCache:
    def __init__(
        self,
        reader: Callable[[], dict] = None,
        ttl_seconds: int = CODEX_QUOTA_CACHE_SECONDS,
        clock: Callable[[], float] = time.time,
    ):
        self.reader = reader or find_latest_codex_quota
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

    for path in session_files:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line in reversed(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = event.get("payload", {})
            rate_limits = payload.get("rate_limits") or event.get("rate_limits")
            if rate_limits:
                return {
                    "available": True,
                    "timestamp": event.get("timestamp"),
                    "rate_limits": rate_limits,
                }

    return {
        "available": False,
        "reason": "no local Codex rate limit snapshot found",
    }
