import subprocess
from collections.abc import Callable


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


def run_command(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def parse_loadavg(text: str) -> dict:
    fields = text.split()
    return {
        "load_1m": float(fields[0]),
        "load_5m": float(fields[1]),
        "load_15m": float(fields[2]),
    }


def parse_meminfo(text: str) -> dict:
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts:
            continue
        values[key] = int(parts[0])

    total_kb = values["MemTotal"]
    available_kb = values["MemAvailable"]
    used_kb = total_kb - available_kb

    return {
        "total_mb": round(total_kb / 1024),
        "available_mb": round(available_kb / 1024),
        "used_mb": round(used_kb / 1024),
        "used_percent": round(used_kb / total_kb * 100, 1),
    }


def parse_int(value: str) -> int | None:
    value = value.strip()
    if value in {"", "[N/A]", "N/A"}:
        return None
    return int(value)


def parse_nvidia_smi(output: str) -> list[dict]:
    gpus = []
    for index, line in enumerate(output.splitlines()):
        if not line.strip():
            continue

        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 5:
            continue

        name = fields[0]
        memory_used = parse_int(fields[1])
        memory_total = parse_int(fields[2])
        utilization = parse_int(fields[3])
        temperature = parse_int(fields[4])
        memory_percent = None
        if memory_used is not None and memory_total:
            memory_percent = round(memory_used / memory_total * 100, 1)

        gpus.append(
            {
                "index": index,
                "name": name,
                "memory_used_mb": memory_used,
                "memory_total_mb": memory_total,
                "memory_used_percent": memory_percent,
                "utilization_percent": utilization,
                "temperature_c": temperature,
            }
        )

    return gpus


class ResourceMonitor:
    def __init__(
        self,
        read_text: Callable[[str], str] = read_file,
        runner: Callable[[list[str]], tuple[int, str, str]] = run_command,
    ):
        self.read_text = read_text
        self.runner = runner

    def collect_load(self) -> dict:
        try:
            return {
                "available": True,
                **parse_loadavg(self.read_text("/proc/loadavg")),
            }
        except (OSError, ValueError, IndexError):
            return {"available": False}

    def collect_memory(self) -> dict:
        try:
            return {
                "available": True,
                **parse_meminfo(self.read_text("/proc/meminfo")),
            }
        except (OSError, KeyError, ValueError, ZeroDivisionError):
            return {"available": False}

    def collect_gpus(self) -> tuple[list[dict], str | None]:
        command = [
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            returncode, stdout, stderr = self.runner(command)
        except OSError as exc:
            return [], str(exc)

        if returncode != 0:
            return [], stderr.strip() or "nvidia-smi failed"

        return parse_nvidia_smi(stdout), None

    def collect(self) -> dict:
        gpus, gpu_error = self.collect_gpus()
        result = {
            "load": self.collect_load(),
            "memory": self.collect_memory(),
            "gpus": gpus,
        }
        if gpu_error:
            result["gpu_error"] = gpu_error
        return result
