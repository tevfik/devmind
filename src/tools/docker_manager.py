"""
Docker Manager (tools module) - Wrapper around CLI docker manager
Re-exports from cli.docker_manager for backward compatibility
"""

from cli.docker_manager import DockerManager

__all__ = ["DockerManager"]
