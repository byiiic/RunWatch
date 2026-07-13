import errno

from backend.ports import PortMonitor, monitored_ports_from_env, parse_lsof_output


def test_monitored_ports_from_env_uses_defaults_when_empty():
    assert monitored_ports_from_env({}) == [8765, 6006, 8000, 8888]


def test_monitored_ports_from_env_parses_unique_ports():
    assert monitored_ports_from_env({"MONITOR_PORTS": "8765, 8888,8765,bad"}) == [
        8765,
        8888,
    ]


def test_parse_lsof_output_extracts_listener():
    output = "\n".join(
        [
            "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME",
            "uvicorn 123 baiyc 7u IPv4 99999 0t0 TCP *:8765 (LISTEN)",
        ]
    )

    result = parse_lsof_output(8765, output)

    assert result == {
        "port": 8765,
        "status": "occupied",
        "occupied": True,
        "pid": 123,
        "command": "uvicorn",
        "user": "baiyc",
        "address": "*:8765",
    }


def test_port_monitor_marks_missing_listener_available():
    def runner(command):
        return 1, "", ""

    def binder(port):
        assert port == 8765

    monitor = PortMonitor(ports=[8765], runner=runner, binder=binder)

    assert monitor.collect() == [
        {
            "port": 8765,
            "status": "available",
            "occupied": False,
            "pid": None,
            "command": None,
            "user": None,
            "address": None,
        }
    ]


def test_port_monitor_marks_hidden_listener_unavailable():
    def runner(command):
        return 1, "", ""

    def binder(port):
        error = OSError("address already in use")
        error.errno = errno.EADDRINUSE
        raise error

    monitor = PortMonitor(ports=[8000], runner=runner, binder=binder)

    assert monitor.collect() == [
        {
            "port": 8000,
            "status": "unavailable",
            "occupied": None,
            "pid": None,
            "command": None,
            "user": None,
            "address": None,
            "error": "address already in use",
        }
    ]


def test_port_monitor_marks_permission_denied_unavailable():
    def runner(command):
        return 1, "", ""

    def binder(port):
        error = OSError("permission denied")
        error.errno = errno.EACCES
        raise error

    monitor = PortMonitor(ports=[80], runner=runner, binder=binder)

    assert monitor.collect()[0]["status"] == "unavailable"


def test_port_monitor_marks_operation_not_permitted_unavailable():
    def runner(command):
        return 1, "", ""

    def binder(port):
        error = OSError("operation not permitted")
        error.errno = errno.EPERM
        raise error

    monitor = PortMonitor(ports=[8000], runner=runner, binder=binder)

    assert monitor.collect()[0]["status"] == "unavailable"


def test_port_monitor_collects_lsof_listener():
    def runner(command):
        assert command == ["lsof", "-nP", "-iTCP:8765", "-sTCP:LISTEN"]
        return (
            0,
            "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n"
            "python 456 baiyc 7u IPv4 99999 0t0 TCP 0.0.0.0:8765 (LISTEN)",
            "",
        )

    monitor = PortMonitor(ports=[8765], runner=runner)

    assert monitor.collect()[0]["pid"] == 456
    assert monitor.collect()[0]["command"] == "python"


def test_port_monitor_marks_lsof_error_unknown():
    def runner(command):
        raise OSError("lsof is not installed")

    monitor = PortMonitor(ports=[8765], runner=runner)

    assert monitor.collect() == [
        {
            "port": 8765,
            "status": "unknown",
            "occupied": None,
            "pid": None,
            "command": None,
            "user": None,
            "address": None,
            "error": "lsof is not installed",
        }
    ]
