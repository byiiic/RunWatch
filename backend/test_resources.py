from backend.resources import (
    ResourceMonitor,
    parse_loadavg,
    parse_meminfo,
    parse_nvidia_smi,
)


def test_parse_loadavg_extracts_load_values():
    assert parse_loadavg("0.12 0.34 0.56 1/234 5678\n") == {
        "load_1m": 0.12,
        "load_5m": 0.34,
        "load_15m": 0.56,
    }


def test_parse_meminfo_calculates_memory_usage():
    meminfo = "\n".join(
        [
            "MemTotal:       1000000 kB",
            "MemAvailable:    250000 kB",
        ]
    )

    assert parse_meminfo(meminfo) == {
        "total_mb": 977,
        "available_mb": 244,
        "used_mb": 732,
        "used_percent": 75.0,
    }


def test_parse_nvidia_smi_extracts_gpu_rows():
    output = "\n".join(
        [
            "NVIDIA RTX 4090, 1024, 24576, 12, 50",
            "NVIDIA RTX 3090, 20000, 24576, 80, 60",
        ]
    )

    assert parse_nvidia_smi(output) == [
        {
            "index": 0,
            "name": "NVIDIA RTX 4090",
            "memory_used_mb": 1024,
            "memory_total_mb": 24576,
            "memory_used_percent": 4.2,
            "utilization_percent": 12,
            "temperature_c": 50,
        },
        {
            "index": 1,
            "name": "NVIDIA RTX 3090",
            "memory_used_mb": 20000,
            "memory_total_mb": 24576,
            "memory_used_percent": 81.4,
            "utilization_percent": 80,
            "temperature_c": 60,
        },
    ]


def test_resource_monitor_collects_cpu_memory_and_gpu():
    def read_text(path):
        if path == "/proc/loadavg":
            return "1.00 2.00 3.00 1/234 5678\n"
        if path == "/proc/meminfo":
            return "MemTotal: 2000000 kB\nMemAvailable: 500000 kB\n"
        raise AssertionError(path)

    def runner(command):
        assert command[0] == "nvidia-smi"
        return 0, "GPU, 100, 1000, 10, 40", ""

    monitor = ResourceMonitor(read_text=read_text, runner=runner)

    assert monitor.collect() == {
        "load": {
            "available": True,
            "load_1m": 1.0,
            "load_5m": 2.0,
            "load_15m": 3.0,
        },
        "memory": {
            "available": True,
            "total_mb": 1953,
            "available_mb": 488,
            "used_mb": 1465,
            "used_percent": 75.0,
        },
        "gpus": [
            {
                "index": 0,
                "name": "GPU",
                "memory_used_mb": 100,
                "memory_total_mb": 1000,
                "memory_used_percent": 10.0,
                "utilization_percent": 10,
                "temperature_c": 40,
            }
        ],
    }


def test_resource_monitor_marks_missing_gpu_as_unavailable():
    def runner(command):
        raise OSError("nvidia-smi missing")

    monitor = ResourceMonitor(
        read_text=lambda path: "",
        runner=runner,
    )

    result = monitor.collect()

    assert result["load"]["available"] is False
    assert result["memory"]["available"] is False
    assert result["gpus"] == []
    assert result["gpu_error"] == "nvidia-smi missing"
