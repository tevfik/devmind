import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ProjectContext(BaseModel):
    repo_id: str
    local_path: str
    project_type: Optional[str] = "python"
    last_analysis: Optional[str] = None


class StateManager:
    """Manages CLI persistent state (current project context, etc.)"""

    def __init__(self):
        self.state_file = Path.home() / ".yaver" / "cli_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text())
        except Exception:
            return {}

    def _save(self):
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def set_current_repo(self, repo_id: str, path: str, type: str = "python"):
        """Sets the active repository context"""
        self._state["current_repo"] = {
            "repo_id": repo_id,
            "local_path": str(path),
            "project_type": type,
        }
        self._save()

    def get_current_repo(self) -> Optional[ProjectContext]:
        """Gets currently active repository context"""
        data = self._state.get("current_repo")
        if not data:
            return None
        return ProjectContext(**data)


# Singleton instance
_state_manager = None


def get_state_manager() -> StateManager:
    global _state_manager
    if not _state_manager:
        _state_manager = StateManager()
    return _state_manager
