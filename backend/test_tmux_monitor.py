from backend.tmux_monitor import TmuxMonitor


def make_pane(command, output=None):
    return {
        "command": command,
        "output": output or [],
    }


def test_uvicorn_command_is_running():
    monitor = TmuxMonitor()

    assert monitor.detect_status(make_pane("uvicorn")) == "running"


def test_uv_command_is_running_for_uvicorn_output():
    monitor = TmuxMonitor()

    pane = make_pane(
        "uv",
        [
            "INFO:     Application startup complete.",
            "INFO:     Uvicorn running on http://0.0.0.0:8765",
        ],
    )

    assert monitor.detect_status(pane) == "running"


def test_service_startup_output_is_running_even_from_shell():
    monitor = TmuxMonitor()

    pane = make_pane(
        "bash",
        ["Uvicorn running on http://0.0.0.0:8765"],
    )

    assert monitor.detect_status(pane) == "running"


def test_error_output_takes_precedence_over_running_command():
    monitor = TmuxMonitor()

    pane = make_pane(
        "uvicorn",
        ["Traceback (most recent call last):"],
    )

    assert monitor.detect_status(pane) == "failed"


def test_error_metric_names_do_not_mark_training_as_failed():
    monitor = TmuxMonitor()

    pane = make_pane(
        ".venv/bin/python",
        [
            "Relative L2 error      : 1.930553e-04",
            "RMS prediction error   : 8.139927e-05",
            "Max absolute error     : 1.077935e-03",
            "WARNING: Falling back to cpu.",
            "Step: 4000 | Loss: 3.2535e-01 | Loss_d: 2.4504e-14",
        ],
    )

    assert monitor.detect_status(pane) == "running"


def test_runtime_error_lines_mark_failed():
    monitor = TmuxMonitor()

    pane = make_pane(
        ".venv/bin/python",
        [
            "RuntimeError: CUDA out of memory",
        ],
    )

    assert monitor.detect_status(pane) == "failed"


def test_service_start_after_old_error_is_running():
    monitor = TmuxMonitor()

    pane = make_pane(
        "uv",
        [
            "ERROR:    [Errno 98] address already in use",
            "INFO:     Started server process [3179951]",
            "INFO:     Waiting for application startup.",
            "INFO:     Application startup complete.",
            "INFO:     Uvicorn running on http://0.0.0.0:8765",
        ],
    )

    assert monitor.detect_status(pane) == "running"


def test_service_error_after_startup_is_failed():
    monitor = TmuxMonitor()

    pane = make_pane(
        "uv",
        [
            "INFO:     Application startup complete.",
            "INFO:     Uvicorn running on http://0.0.0.0:8765",
            "Traceback (most recent call last):",
        ],
    )

    assert monitor.detect_status(pane) == "failed"
