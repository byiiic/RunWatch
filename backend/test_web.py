import importlib

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse


def load_web(monkeypatch, token=None):
    if token is None:
        monkeypatch.delenv("MONITOR_TOKEN", raising=False)
    else:
        monkeypatch.setenv("MONITOR_TOKEN", token)

    import backend.web as web

    return importlib.reload(web)


def test_token_loads_from_env_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MONITOR_TOKEN", raising=False)
    tmp_path.joinpath(".env").write_text("MONITOR_TOKEN=from-file\n")

    import backend.web as web

    web = importlib.reload(web)

    assert web.MONITOR_TOKEN == "from-file"
    assert web.require_token(authorization="Bearer from-file") is None


def test_environment_token_overrides_env_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MONITOR_TOKEN", "from-env")
    tmp_path.joinpath(".env").write_text("MONITOR_TOKEN=from-file\n")

    import backend.web as web

    web = importlib.reload(web)

    assert web.MONITOR_TOKEN == "from-env"


def test_ports_load_from_env_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MONITOR_TOKEN", raising=False)
    monkeypatch.delenv("MONITOR_PORTS", raising=False)
    tmp_path.joinpath(".env").write_text(
        "MONITOR_TOKEN=from-file\n"
        "MONITOR_PORTS=8765,8888\n"
    )

    import backend.web as web

    web = importlib.reload(web)

    assert web.app.state.port_monitor.ports == [8765, 8888]


def test_environment_ports_do_not_override_env_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MONITOR_TOKEN", "from-env")
    monkeypatch.setenv("MONITOR_PORTS", "6006,8000")
    tmp_path.joinpath(".env").write_text(
        "MONITOR_TOKEN=from-file\n"
        "MONITOR_PORTS=8765,8888\n"
    )

    import backend.web as web

    web = importlib.reload(web)

    assert web.app.state.port_monitor.ports == [8765, 8888]


def test_health_reports_ok(monkeypatch):
    web = load_web(monkeypatch)

    assert web.health() == {"ok": True}


def test_status_returns_panes_from_monitor(monkeypatch):
    web = load_web(monkeypatch, token="secret")

    sample = [
        {
            "session": "work",
            "window": 0,
            "window_name": "shell",
            "pane_index": 0,
            "pane_id": "%1",
            "pid": 123,
            "command": "bash",
            "path": "/tmp",
            "output": ["ready"],
            "activity": "1783932000",
            "status": "running",
            "collected_at": "2026-07-13T16:55:00",
        }
    ]

    class FakeMonitor:
        def collect(self):
            return sample

    class FakeQuotaCache:
        def get(self):
            return {"available": True}

    class FakePortMonitor:
        def collect(self):
            return [{"port": 8765, "occupied": True}]

    class FakeResourceMonitor:
        def collect(self):
            return {"memory": {"available": True}}

    web.app.state.monitor = FakeMonitor()
    web.app.state.codex_quota_cache = FakeQuotaCache()
    web.app.state.port_monitor = FakePortMonitor()
    web.app.state.resource_monitor = FakeResourceMonitor()

    response = web.status()

    assert response["panes"] == sample
    assert response["count"] == 1
    assert "served_at" in response
    assert response["codex_quota"] == {"available": True}
    assert response["ports"] == [{"port": 8765, "occupied": True}]
    assert response["resources"] == {"memory": {"available": True}}


def test_status_reports_monitor_errors(monkeypatch):
    web = load_web(monkeypatch, token="secret")

    class BrokenMonitor:
        def collect(self):
            raise RuntimeError("tmux unavailable")

    web.app.state.monitor = BrokenMonitor()

    with pytest.raises(HTTPException) as error:
        web.status()

    assert error.value.status_code == 503
    assert error.value.detail == "tmux unavailable"


def test_token_protects_status_when_configured(monkeypatch):
    web = load_web(monkeypatch, token="secret")

    class FakeMonitor:
        def collect(self):
            return []

    web.app.state.monitor = FakeMonitor()

    with pytest.raises(HTTPException) as error:
        web.require_token(authorization=None)

    assert error.value.status_code == 401
    assert web.require_token(authorization="Bearer secret") is None


def test_missing_token_fails_closed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    web = load_web(monkeypatch)

    with pytest.raises(HTTPException) as error:
        web.require_token(authorization=None)

    assert error.value.status_code == 503
    assert error.value.detail == "monitor token is not configured"


def test_query_token_is_not_accepted(monkeypatch):
    web = load_web(monkeypatch, token="secret")

    with pytest.raises(TypeError):
        web.require_token(token="secret", authorization=None)


def test_index_serves_dashboard(monkeypatch):
    web = load_web(monkeypatch)

    response = web.index()

    assert isinstance(response, FileResponse)
    assert response.path.name == "index.html"
    html = response.path.read_text()
    assert "RunWatch" in html
    assert "/api/status" in html
    assert "?token=" not in html
    assert "Authorization" in html
    assert '<body id="top">' in html
    assert 'class="brand-link" href="#top"' in html
    assert 'id="overview"' in html
    assert 'id="sessions"' in html
    assert 'id="resources"' in html
    assert 'id="ports"' in html
    assert 'id="quota"' in html
    assert "codex_quota" in html
    assert "renderOverview(data)" in html
    assert "resourceSummary" in html
    assert "overview-meta" in html
    assert "overview-detail" in html
    assert "scroll-padding-top" in html
    assert "#updated" in html
    assert 'id="updated-short"' in html
    assert "toLocaleTimeString" in html
    assert 'minute: "2-digit"' in html
    assert 'target: "#sessions"' in html
    assert 'target: "#resources"' in html
    assert 'target: "#ports"' in html
    assert 'target: "#quota"' in html
    assert "Details >" in html
    assert "GPU util" in html
    assert "Mem" in html
    assert "groupPanesBySession" in html
    assert "renderPanes(data.panes)" in html
    assert 'class="session-group"' in html
