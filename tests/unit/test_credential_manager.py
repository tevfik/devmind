import unittest
import json
import shutil
from pathlib import Path
from tools.forge.credential_manager import CredentialManager, ForgeHostConfig

class TestCredentialManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("./tests/temp_config")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.manager = CredentialManager(config_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_save_and_load_host(self):
        cfg = ForgeHostConfig(provider="gitea", token="xyz", api_url="https://gitea.test")
        self.manager.save_host("gitea.test", cfg)

        # reload
        manager2 = CredentialManager(config_dir=self.test_dir)
        loaded = manager2.get_host_config("gitea.test")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.token, "xyz")
        self.assertEqual(loaded.provider, "gitea")

    def test_detect_host(self):
        # Setup specific host
        self.manager.hosts["gitea.company.com"] = ForgeHostConfig(provider="gitea", token="token")
        
        url1 = "https://gitea.company.com/user/repo"
        self.assertEqual(self.manager.detect_host_from_url(url1), "gitea.company.com")

        url2 = "git@gitea.company.com:user/repo.git"
        self.assertEqual(self.manager.detect_host_from_url(url2), "gitea.company.com")

        url3 = "https://github.com/user/repo"
        self.assertIsNone(self.manager.detect_host_from_url(url3)) # Not in config

if __name__ == "__main__":
    unittest.main()
