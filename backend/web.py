import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from backend.codex_quota import CodexQuotaCache
from backend.ports import PortMonitor, monitored_ports_from_env
from backend.tmux_monitor import TmuxMonitor


STATIC_DIR = Path(__file__).parent / "static"
ENV_FILE = Path.cwd() / ".env"


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}

    values = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    return values


def get_setting(name: str) -> str | None:
    return os.environ.get(name) or read_env_file().get(name)


MONITOR_TOKEN = get_setting("MONITOR_TOKEN")
MONITOR_PORTS = monitored_ports_from_env(read_env_file())


app = FastAPI(
    title="Tmux Monitor",
    version="0.1.0",
)
app.state.monitor = TmuxMonitor(output_lines=12)
app.state.codex_quota_cache = CodexQuotaCache()
app.state.port_monitor = PortMonitor(ports=MONITOR_PORTS)


def require_token(authorization: str | None = Header(default=None)):
    if not MONITOR_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="monitor token is not configured",
        )

    bearer = "Bearer "
    auth_token = None
    if authorization and authorization.startswith(bearer):
        auth_token = authorization[len(bearer):]

    if auth_token == MONITOR_TOKEN:
        return

    raise HTTPException(
        status_code=401,
        detail="missing or invalid token",
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status(_: None = Depends(require_token)):
    try:
        panes = app.state.monitor.collect()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return {
        "served_at": datetime.now().isoformat(),
        "count": len(panes),
        "panes": panes,
        "ports": app.state.port_monitor.collect(),
        "codex_quota": app.state.codex_quota_cache.get(),
    }
