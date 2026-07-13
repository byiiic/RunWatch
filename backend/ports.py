import errno
import re
import socket
import subprocess
from collections.abc import Callable


DEFAULT_MONITORED_PORTS = [8765, 6006, 8000, 8888]


def monitored_ports_from_env(env: dict[str, str] | None = None) -> list[int]:
    value = (env or {}).get("MONITOR_PORTS", "")
    if not value.strip():
        return DEFAULT_MONITORED_PORTS.copy()

    ports = []
    seen = set()
    for raw_port in value.split(","):
        try:
            port = int(raw_port.strip())
        except ValueError:
            continue

        if port < 1 or port > 65535 or port in seen:
            continue

        ports.append(port)
        seen.add(port)

    return ports or DEFAULT_MONITORED_PORTS.copy()


def run_lsof(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def empty_port(port: int) -> dict:
    return {
        "port": port,
        "status": "available",
        "occupied": False,
        "pid": None,
        "command": None,
        "user": None,
        "address": None,
    }


def unknown_port(port: int, error: str) -> dict:
    return {
        "port": port,
        "status": "unknown",
        "occupied": None,
        "pid": None,
        "command": None,
        "user": None,
        "address": None,
        "error": error,
    }


def unavailable_port(port: int, error: str) -> dict:
    return {
        "port": port,
        "status": "unavailable",
        "occupied": None,
        "pid": None,
        "command": None,
        "user": None,
        "address": None,
        "error": error,
    }


def can_bind_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("0.0.0.0", port))


def parse_lsof_output(port: int, output: str) -> dict:
    for line in output.splitlines()[1:]:
        fields = line.split(None, 8)
        if len(fields) < 9:
            continue

        name = fields[8]
        match = re.search(r"(?P<address>\S*:%d)\s+\(LISTEN\)" % port, name)
        if not match:
            continue

        try:
            pid = int(fields[1])
        except ValueError:
            pid = None

        return {
            "port": port,
            "status": "occupied",
            "occupied": True,
            "pid": pid,
            "command": fields[0],
            "user": fields[2],
            "address": match.group("address"),
        }

    return empty_port(port)


class PortMonitor:
    def __init__(
        self,
        ports: list[int] | None = None,
        runner: Callable[[list[str]], tuple[int, str, str]] = run_lsof,
        binder: Callable[[int], None] = can_bind_port,
    ):
        self.ports = ports or monitored_ports_from_env()
        self.runner = runner
        self.binder = binder

    def collect(self) -> list[dict]:
        results = []

        for port in self.ports:
            command = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"]
            try:
                returncode, stdout, _stderr = self.runner(command)
            except OSError as exc:
                results.append(unknown_port(port, str(exc)))
                continue

            if returncode != 0:
                results.append(self.probe_port(port))
                continue

            results.append(parse_lsof_output(port, stdout))

        return results

    def probe_port(self, port: int) -> dict:
        try:
            self.binder(port)
        except OSError as exc:
            if exc.errno in {errno.EADDRINUSE, errno.EACCES, errno.EPERM}:
                return unavailable_port(port, str(exc))
            return unknown_port(port, str(exc))

        return empty_port(port)
