import requests
from typing import List, Dict, Any
from tools.forge.provider import ForgeProvider

class GiteaAdapter(ForgeProvider):
    """
    Gitea implementation of ForgeProvider using requests.
    """

    def __init__(self, base_url: str, token: str, owner: str, repo: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.api_url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}"

    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        url = f"{self.api_url}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_pr(self, pr_id: int) -> Dict[str, Any]:
        url = f"{self.api_url}/pulls/{pr_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        url = f"{self.api_url}/issues"
        params = {"state": state}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_issue_comment(self, issue_id: int, body: str) -> Dict[str, Any]:
        # Gitea treats PRs as issues for comments
        url = f"{self.api_url}/issues/{issue_id}/comments"
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
