import json

from backend.codex_quota import CodexQuotaCache, find_latest_codex_quota


def write_jsonl(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event) for event in events),
        encoding="utf-8",
    )


def test_finds_latest_rate_limits_from_session_logs(tmp_path):
    older = tmp_path / "sessions" / "2026" / "07" / "01" / "older.jsonl"
    newer = tmp_path / "sessions" / "2026" / "07" / "13" / "newer.jsonl"

    write_jsonl(
        older,
        [
            {
                "timestamp": "2026-07-01T00:00:00Z",
                "payload": {
                    "rate_limits": {
                        "limit_id": "codex",
                        "primary": {"used_percent": 10.0, "resets_at": 1},
                    }
                },
            }
        ],
    )
    write_jsonl(
        newer,
        [
            {"timestamp": "2026-07-13T00:00:00Z", "payload": {}},
            {
                "timestamp": "2026-07-13T00:01:00Z",
                "payload": {
                    "rate_limits": {
                        "limit_id": "codex",
                        "plan_type": "pro",
                        "primary": {
                            "used_percent": 74.0,
                            "window_minutes": 300,
                            "resets_at": 1782982187,
                        },
                        "secondary": {
                            "used_percent": 97.0,
                            "window_minutes": 10080,
                            "resets_at": 1783388818,
                        },
                    }
                },
            },
        ],
    )

    result = find_latest_codex_quota(tmp_path)

    assert result["available"] is True
    assert result["timestamp"] == "2026-07-13T00:01:00Z"
    assert "source" not in result
    assert result["rate_limits"]["plan_type"] == "pro"
    assert result["rate_limits"]["primary"]["used_percent"] == 74.0
    assert result["rate_limits"]["secondary"]["used_percent"] == 97.0


def test_returns_unavailable_when_no_rate_limits_exist(tmp_path):
    session = tmp_path / "sessions" / "empty.jsonl"
    write_jsonl(session, [{"timestamp": "2026-07-13T00:00:00Z", "payload": {}}])

    result = find_latest_codex_quota(tmp_path)

    assert result == {
        "available": False,
        "reason": "no local Codex rate limit snapshot found",
    }


def test_skips_invalid_json_lines(tmp_path):
    session = tmp_path / "sessions" / "mixed.jsonl"
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(
        "{not json}\n"
        + json.dumps(
            {
                "timestamp": "2026-07-13T00:00:00Z",
                "rate_limits": {"limit_id": "codex"},
            }
        ),
        encoding="utf-8",
    )

    result = find_latest_codex_quota(tmp_path)

    assert result["available"] is True
    assert result["rate_limits"]["limit_id"] == "codex"


def test_quota_cache_reuses_snapshot_until_ttl_expires():
    calls = []
    now = {"value": 1000.0}

    def reader():
        calls.append(now["value"])
        return {"available": True, "read_at": now["value"]}

    cache = CodexQuotaCache(
        reader=reader,
        ttl_seconds=120,
        clock=lambda: now["value"],
    )

    assert cache.get()["read_at"] == 1000.0
    now["value"] = 1050.0
    assert cache.get()["read_at"] == 1000.0
    now["value"] = 1121.0
    assert cache.get()["read_at"] == 1121.0
    assert calls == [1000.0, 1121.0]
