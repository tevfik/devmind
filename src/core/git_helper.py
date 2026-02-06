"""
Git utilities for project analysis.

Provides commit tracking, diff detection, and history analysis.
unified from src/core/git_helper.py and src/tools/git/client.py
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Set

logger = logging.getLogger(__name__)


class GitHelper:
    """Git utilities for analysis integration."""

    def __init__(self, repo_path: Union[str, Path]):
        """Initialize git helper for a repository."""
        self.repo_path = Path(repo_path)

    @property
    def is_git_repo(self) -> bool:
        """Check if path is a git repository (property alias for is_repository)."""
        return self.is_repository()

    def is_repository(self) -> bool:
        """Check if path is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Failed to get current commit: {e}")
            return None

    def get_changed_files(self, since_commit: str) -> Optional[List[str]]:
        """
        Get files changed between a commit and HEAD.

        Returns:
            List of file paths, or None if error
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{since_commit}..HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]

            return None
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return None

    def get_commit_count(self) -> int:
        """Get total commit count."""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            return 0

    def is_ancestor(self, ancestor_commit: str, descendant_commit: str) -> bool:
        """Check if ancestor_commit is an ancestor of descendant_commit."""
        try:
            result = subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    ancestor_commit,
                    descendant_commit,
                ],
                cwd=self.repo_path,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    # --- Methods ported from GitClient ---

    def list_files(self) -> List[str]:
        """List tracked files."""
        if not self.is_repository():
            # Fallback to os walk
            return [
                str(p)
                for p in self.repo_path.rglob("*")
                if p.is_file() and ".git" not in str(p)
            ]

        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return result.stdout.splitlines()
        except Exception:
            return []

    def get_status(self) -> Dict[str, Any]:
        """Get git repository status"""
        if not self.is_repository():
            return {"error": "Not a git repository"}

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            return {
                "status": "ok",
                "changes": result.stdout,
                "is_clean": result.returncode == 0 and not result.stdout,
                "active_branch": self.get_branch(),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits"""
        if not self.is_repository():
            return []

        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    commits.append(
                        {
                            "hash": parts[0],
                            "message": parts[1] if len(parts) > 1 else "",
                        }
                    )

            return commits
        except Exception:
            return []

    def get_branch(self) -> Optional[str]:
        """Get current branch"""
        if not self.is_repository():
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            return result.stdout.strip()
        except Exception:
            return None

    def get_files_changed_against_target(self, target: str) -> List[str]:
        """
        Get files changed against a specific target (commit or branch).
        Equivalent to `get_changed_files_since` in GitClient.
        """
        if not self.is_repository():
            return []

        try:
            # git diff --name-only <target> compares working tree to target
            result = subprocess.run(
                ["git", "diff", "--name-only", target],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return [f for f in result.stdout.splitlines() if f.strip()]
        except Exception:
            return []

    def get_remotes(self) -> List[str]:
        """Get configured remotes"""
        if not self.is_repository():
            return []

        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            remotes = set()
            for line in result.stdout.strip().split("\n"):
                if line:
                    remotes.add(line.split()[0])

            return list(remotes)
        except Exception:
            return []

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """Get URL for a specific remote."""
        if not self.is_repository():
            return None

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", remote],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    @staticmethod
    def clone(repo_url: str, target_path: str) -> bool:
        """Clone a repository to a target path."""
        try:
            subprocess.run(
                ["git", "clone", repo_url, target_path], check=True, capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def checkout_pr(self, pr_number: int, remote: str = "origin") -> bool:
        """Fetch and checkout a PR by number (GitHub/Gitea/GitLab style refs)."""
        if not self.is_repository():
            return False

        try:
            # 1. Fetch the PR ref to a local branch
            branch_name = f"pr-{pr_number}"
            # Standard GitHub/Gitea ref: refs/pull/ID/head
            ref_spec = f"refs/pull/{pr_number}/head"

            fetch_cmd = ["git", "fetch", remote, f"{ref_spec}:{branch_name}"]
            subprocess.run(fetch_cmd, cwd=self.repo_path, check=True)

            # 2. Checkout the branch
            subprocess.run(
                ["git", "checkout", branch_name], cwd=self.repo_path, check=True
            )
            return True
        except Exception:
            # Fallback: maybe it's GitLab? refs/merge-requests/ID/head
            try:
                ref_spec = f"refs/merge-requests/{pr_number}/head"
                fetch_cmd = ["git", "fetch", remote, f"{ref_spec}:{branch_name}"]
                subprocess.run(fetch_cmd, cwd=self.repo_path, check=True)
                subprocess.run(
                    ["git", "checkout", branch_name], cwd=self.repo_path, check=True
                )
                return True
            except:
                # Try to just checkout if it already exists locally
                try:
                    subprocess.run(
                        ["git", "checkout", f"pr-{pr_number}"],
                        cwd=self.repo_path,
                        check=True,
                    )
                    return True
                except:
                    return False

    def get_diff(self, target: str = "HEAD") -> str:
        """Get diff of current changes or compare with target."""
        try:
            res = subprocess.run(
                ["git", "diff", target],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return res.stdout
        except:
            return ""
