"""
Git Analyzer - Analyzes git repositories
Refactored to use src/core/git_helper.py common logic
"""

from pathlib import Path
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from tools.base import Tool
from core.git_helper import GitHelper


class GitClientSchema(BaseModel):
    command: str = Field(
        ..., description="Git operation: 'status', 'log', 'branch', 'diff', 'ls'"
    )
    arg: Optional[str] = Field(
        None, description="Optional argument (e.g. commit hash for diff)"
    )


class GitClient(Tool):
    """
    Analyzes git repositories for commits, changes, and history.
    """

    name = "git_client"
    description = "Read-only Git operations (status, log, diff, ls)"
    args_schema = GitClientSchema

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize git analyzer"""
        self.repo_path = Path(repo_path or ".")
        self.helper = GitHelper(self.repo_path)

    @property
    def is_git_repo(self) -> bool:
        """Check if path is a git repository."""
        return self.helper.is_git_repo

    def run(self, command: str, arg: Optional[str] = None, **kwargs) -> Any:
        """Execute git command (wrapper for methods)."""
        mapping = {
            "status": "get_status",
            "log": "get_commits",
            "branch": "get_branch",
            "diff": "get_changed_files_since",
            "ls": "list_files",
        }

        method_name = mapping.get(command, command)
        method = getattr(self, method_name, None)

        if method:
            # Fix for diff without args
            if command == "diff":
                if arg:
                    return method(arg)
                return self.get_status()  # Fallback to status if no commit hash

            return method()

        return {"error": f"Unknown command: {command}"}

    def list_files(self) -> List[str]:
        """List tracked files."""
        return self.helper.list_files()

    def get_status(self) -> Dict[str, Any]:
        """Get git repository status"""
        return self.helper.get_status()

    def get_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits"""
        return self.helper.get_commits(count)

    def get_branch(self) -> Optional[str]:
        """Get current branch"""
        return self.helper.get_branch()

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        return self.helper.get_current_commit()

    def get_changed_files_since(self, commit_hash: str) -> List[str]:
        """Get list of files changed since a specific commit"""
        return self.helper.get_files_changed_against_target(commit_hash)

    def get_remotes(self) -> List[str]:
        """Get configured remotes"""
        return self.helper.get_remotes()

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """Get URL for a specific remote."""
        return self.helper.get_remote_url(remote)

    @staticmethod
    def clone(repo_url: str, target_path: str) -> bool:
        """Clone a repository to a target path."""
        return GitHelper.clone(repo_url, target_path)

    def checkout_pr(self, pr_number: int, remote: str = "origin") -> bool:
        """Fetch and checkout a PR by number."""
        return self.helper.checkout_pr(pr_number, remote)

    def get_diff(self, target: str = "HEAD") -> str:
        """Get diff of current changes or compare with target."""
        return self.helper.get_diff(target)
