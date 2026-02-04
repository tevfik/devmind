"""
Docker Manager Tool
Wraps cli.docker_manager for Agent use.
"""

from typing import Any
from tools.base import Tool
from cli.docker_manager import DockerManager as CLIDockerManager


class DockerManager(Tool):
    """
    Manages Docker services via the CLI manager.
    """

    name = "docker_manager"
    description = "Manage Docker services (start, stop, status, restart)"

    def __init__(self):
        self.manager = CLIDockerManager()

    def run(self, command: str, **kwargs) -> Any:
        # Map agent commands to CLI manager methods
        if command == "status":
            return (
                self.manager.print_status()
            )  # This prints to stdout, might need capture
        elif command == "start":
            return self.manager.start_services()
        elif command == "stop":
            return self.manager.stop_services()
        elif command == "restart":
            self.manager.stop_services(verbose=False)
            return self.manager.start_services()

        return {"error": f"Unknown docker command: {command}"}
