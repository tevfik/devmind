"""
Shell Tools
"""

import subprocess
import shlex
from typing import Any, List
from tools.base import Tool


class ShellTool(Tool):
    name = "shell_run"
    description = "Run shell command"

    _BLACKLIST = ["rm -rf /", "rm -rf /*", ":(){ :|:& };:", "mkfs", "dd"]  # Fork bomb

    def run(self, command: str, **kwargs) -> Any:
        # Basic safety check
        for bad in self._BLACKLIST:
            if bad in command:
                return f"Error: Command {command} is not allowed."

        try:
            # Split command for subprocess (if shell=False, but here we likely want shell=True flexibility for now)
            # Using shell=True for complex commands (pipes etc) but constrained.
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as e:
            return f"Error running command: {e}"
