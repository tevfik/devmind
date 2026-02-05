from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ForgeProvider(ABC):
    """
    Abstract Base Class for Git Forge Providers (GitHub, Gitea, GitLab).
    """

    @abstractmethod
    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        """Create a Pull Request."""
        pass

    @abstractmethod
    def get_pr(self, pr_id: int) -> Dict[str, Any]:
        """Get details of a Pull Request."""
        pass

    @abstractmethod
    def list_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in the repository."""
        pass

    @abstractmethod
    def create_issue_comment(self, issue_id: int, body: str) -> Dict[str, Any]:
        """Add a comment to an issue or PR."""
        pass
