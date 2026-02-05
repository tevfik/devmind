from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
from tools.base import Tool
from tools.forge.provider import ForgeProvider
from tools.forge.adapters.gitea import GiteaAdapter
from config.config import FORGE_PROVIDER, FORGE_URL, FORGE_TOKEN, FORGE_OWNER, FORGE_REPO

class ForgeToolSchema(BaseModel):
    command: str = Field(..., description="Forge operation: 'create_pr', 'list_issues', 'get_pr', 'comment_issue'")
    title: Optional[str] = Field(None, description="Title for PR")
    body: Optional[str] = Field(None, description="Body for PR or comment")
    head: Optional[str] = Field(None, description="Head branch for PR (e.g. feature-branch)")
    base: Optional[str] = Field(None, description="Base branch for PR (e.g. main)")
    issue_id: Optional[int] = Field(None, description="Issue or PR ID for comments/details")

class ForgeTool(Tool):
    """
    Tool for interacting with remote Git forges (Gitea/GitHub).
    """
    name = "forge_tool"
    description = "Interact with remote Git forge (Gitea/GitHub) to manage PRs and Issues."
    args_schema = ForgeToolSchema

    def __init__(self):
        self.provider: Optional[ForgeProvider] = None
        self._initialize_provider()

    def _initialize_provider(self):
        # 1. Try Dynamic Detection from Git Config
        try:
            from tools.git.client import GitClient
            from tools.forge.credential_manager import CredentialManager
            
            git = GitClient()
            remote_url = git.get_remote_url()
            
            if remote_url:
                creds = CredentialManager()
                host = creds.detect_host_from_url(remote_url)
                
                if host:
                    config = creds.get_host_config(host)
                    if config and config.provider == "gitea":
                        # Extract owner/repo from URL
                        # URL: https://gitea.com/owner/repo.git
                        parts = remote_url.rstrip(".git").split("/")
                        repo = parts[-1]
                        owner = parts[-2]
                        
                        api_url = config.api_url or f"https://{host}"
                        self.provider = GiteaAdapter(api_url, config.token, owner, repo)
                        return
                    # Add GitHub execution branch here
        except ImportError:
            pass # Dependencies might not be ready

        # 2. Fallback to Environment Variables (Legacy/Single Mode)
        if FORGE_PROVIDER == "gitea":
            if FORGE_URL and FORGE_TOKEN:
                self.provider = GiteaAdapter(FORGE_URL, FORGE_TOKEN, FORGE_OWNER, FORGE_REPO)

    def run(self, command: str, **kwargs) -> Any:
        if not self.provider:
            return "Error: Forge provider not configured. Check FORGE_PROVIDER, FORGE_URL, and FORGE_TOKEN in config."

        try:
            if command == "create_pr":
                return self.provider.create_pr(
                    kwargs.get("title"),
                    kwargs.get("body"),
                    kwargs.get("head"),
                    kwargs.get("base")
                )
            elif command == "list_issues":
                return self.provider.list_issues()
            elif command == "get_pr":
                return self.provider.get_pr(kwargs.get("issue_id"))
            elif command == "comment_issue":
                return self.provider.create_issue_comment(
                    kwargs.get("issue_id"),
                    kwargs.get("body")
                )
            else:
                return f"Error: Unknown command '{command}'"
        except Exception as e:
            return f"Error executing {command}: {str(e)}"
