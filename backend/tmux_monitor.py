import re
import subprocess
import json
import time
from datetime import datetime


class TmuxMonitor:
    """
    Collect tmux session/window/pane status.

    Phase 1:
    - discover panes
    - capture output
    - estimate status
    """

    def __init__(
        self,
        output_lines=50
    ):
        self.output_lines = output_lines


    # -----------------------------
    # execute tmux command
    # -----------------------------
    def run_command(self, cmd):

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
            )

        return result.stdout.strip()


    # -----------------------------
    # list all panes
    # -----------------------------
    def get_panes(self):

        format_str = (
            "#{session_name}|"
            "#{window_index}|"
            "#{window_name}|"
            "#{pane_index}|"
            "#{pane_id}|"
            "#{pane_pid}|"
            "#{pane_current_command}|"
            "#{pane_current_path}"
        )


        cmd = (
            "tmux list-panes -a "
            "-F "
            f"'{format_str}'"
        )


        try:
            output = self.run_command(cmd)

        except RuntimeError:

            # no tmux session
            return []


        if not output:
            return []


        panes = []


        for line in output.splitlines():

            fields = line.split("|")


            if len(fields) != 8:
                continue


            (
                session,
                window,
                window_name,
                pane_index,
                pane_id,
                pane_pid,
                command,
                path
            ) = fields


            panes.append(
                {
                    "session": session,
                    "window": int(window),
                    "window_name": window_name,
                    "pane_index": int(pane_index),
                    "pane_id": pane_id,
                    "pid": int(pane_pid),
                    "command": command,
                    "path": path,
                }
            )


        return panes



    # -----------------------------
    # capture terminal output
    # -----------------------------
    def capture_output(
        self,
        pane_id
    ):

        cmd = (
            f"tmux capture-pane "
            f"-t {pane_id} "
            f"-p "
            f"-S -{self.output_lines}"
        )


        try:

            output = self.run_command(cmd)

        except RuntimeError:

            return []


        if not output:
            return []


        return output.splitlines()



    # -----------------------------
    # get pane activity time
    # -----------------------------
    def get_activity_time(
        self,
        pane_id
    ):

        try:

            cmd = (
                f"tmux display-message "
                f"-p "
                f"-t {pane_id} "
                "'#{pane_activity}'"
            )


            value = self.run_command(cmd)

            return value


        except Exception:

            return None



    # -----------------------------
    # simple status detector
    # -----------------------------
    def detect_status(
        self,
        pane
    ):

        output_lines = [
            line.lower()
            for line in pane.get(
                "output",
                []
            )
        ]

        output = "\n".join(output_lines)


        command = pane["command"]
        command_name = command.lower().rsplit("/", 1)[-1]


        # Error metrics such as "Relative L2 error" are normal training output,
        # so only match lines that look like actual runtime failures.
        failure_patterns = [
            r"\btraceback\b",
            r"\bexception\b",
            r"\b[a-z_]*error:",
            r"^\s*(error|fatal|critical)\s*:",
            r"\bfailed\b",
            r"\bsegmentation fault\b",
            r"\bout of memory\b",
        ]


        service_markers = [
            "application startup complete",
            "uvicorn running on",
            "running on http://",
            "server running",
            "listening on",
            "started server process",
        ]


        latest_failure = -1
        latest_service = -1

        for index, line in enumerate(output_lines):

            if any(
                re.search(pattern, line)
                for pattern in failure_patterns
            ):

                latest_failure = index

            if any(marker in line for marker in service_markers):

                latest_service = index

        if latest_failure > latest_service:

            return "failed"

        if latest_service >= 0:

            return "running"



        # interactive shells
        running_commands = [
            "python",
            "python3",
            "uv",
            "uvicorn",
            "fastapi",
            "codex",
            "bash",
            "zsh",
            "julia",
            "matlab",
            "node",
            "npm",
            "pnpm",
            "vite"
        ]


        if command_name in running_commands:

            return "running"



        return "idle"



    # -----------------------------
    # collect complete state
    # -----------------------------
    def collect(self):

        panes = self.get_panes()


        timestamp = datetime.now().isoformat()


        for pane in panes:


            pane["output"] = (
                self.capture_output(
                    pane["pane_id"]
                )
            )


            pane["activity"] = (
                self.get_activity_time(
                    pane["pane_id"]
                )
            )


            pane["status"] = (
                self.detect_status(
                    pane
                )
            )


            pane["collected_at"] = timestamp



        return panes



# -----------------------------------
# standalone test
# -----------------------------------
if __name__ == "__main__":


    monitor = TmuxMonitor(
        output_lines=30
    )


    result = monitor.collect()


    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
