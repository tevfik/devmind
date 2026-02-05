import unittest
from unittest.mock import MagicMock, patch
from tools.forge.adapters.gitea import GiteaAdapter

class TestGiteaAdapter(unittest.TestCase):

    def setUp(self):
        self.base_url = "https://gitea.example.com"
        self.token = "fake_token"
        self.owner = "admin"
        self.repo = "yaver"
        self.adapter = GiteaAdapter(self.base_url, self.token, self.owner, self.repo)

    @patch("tools.forge.adapters.gitea.requests.Session")
    def test_create_pr(self, mock_session):
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "title": "Test PR", "url": "http://gitea/pr/1"}
        mock_response.status_code = 201
        
        # Configure session mock to return our mock response
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response
        self.adapter.session = mock_session_instance # Inject mock session

        # Call method
        result = self.adapter.create_pr("Test PR", "Body", "feature", "main")
        
        # Verify
        self.assertEqual(result["title"], "Test PR")
        self.adapter.session.post.assert_called_once()
        args, kwargs = self.adapter.session.post.call_args
        self.assertIn("/repos/admin/yaver/pulls", args[0])
        self.assertEqual(kwargs["json"], {
            "title": "Test PR", 
            "body": "Body", 
            "head": "feature", 
            "base": "main"
        })

    @patch("tools.forge.adapters.gitea.requests.Session")
    def test_list_issues(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Bug"}]
        mock_response.status_code = 200
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = mock_response
        self.adapter.session = mock_session_instance

        results = self.adapter.list_issues()
        self.assertEqual(len(results), 1)
        self.adapter.session.get.assert_called_with(
            "https://gitea.example.com/api/v1/repos/admin/yaver/issues", 
            params={"state": "open"}
        )

if __name__ == "__main__":
    unittest.main()
