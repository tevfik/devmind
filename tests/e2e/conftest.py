import pytest
import subprocess
import time
import requests
import os
import shutil

# Configuration for Test Environment
GITEA_URL = "http://localhost:3000"
API_URL = f"{GITEA_URL}/api/v1"
ADMIN_USER = "yaver_admin"
ADMIN_PASS = "yaver_password_123"
TEST_REPO_NAME = "e2e_test_repo"


@pytest.fixture(scope="session")
def docker_env():
    """Ensure docker-compose-test.yml is up."""
    # This assumes docker-compose is installed
    # Spin up
    compose_file = os.path.join(
        os.path.dirname(__file__), "../../docker/docker-compose-test.yml"
    )
    subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d"], check=True)

    # Wait for Gitea to be healthy
    print("Waiting for Gitea to start...")
    max_retries = 60
    for _ in range(max_retries):
        try:
            resp = requests.get(GITEA_URL)
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        pytest.fail("Gitea did not start in time")

    # Wait for Qdrant
    print("Waiting for Qdrant...")
    for _ in range(max_retries):
        try:
            resp = requests.get("http://localhost:6335/readyz")
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        # Don't fail hard if just testing Gitea, but good to know
        print("Warning: Qdrant did not start in time")

    # Wait for Neo4j
    print("Waiting for Neo4j...")
    for _ in range(max_retries):
        try:
            # Neo4j HTTP interface
            resp = requests.get("http://localhost:7475")
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        print("Warning: Neo4j did not start in time")

    yield

    # Tear down (optional, maybe keep for debugging)
    # subprocess.run(["docker-compose", "-f", compose_file, "down"])


@pytest.fixture(scope="session")
def admin_token(docker_env):
    """Create admin user and return token."""
    # In a real scenario, we might need to use the 'gitea admin user create' CLI command
    # inside the container because API token creation needs basic auth first.

    cmd = [
        "docker",
        "exec",
        "yaver_test_gitea",
        "su",
        "git",
        "-c",
        f"gitea admin user create --username {ADMIN_USER} --password {ADMIN_PASS} --email admin@test.local --admin",
    ]
    # Ignore error if user exists
    subprocess.run(cmd, check=False)

    # 1. Check if token exists and delete if so
    auth = (ADMIN_USER, ADMIN_PASS)
    list_resp = requests.get(f"{API_URL}/users/{ADMIN_USER}/tokens", auth=auth)

    if list_resp.status_code == 200:
        for t in list_resp.json():
            if t["name"] == "test_token":
                # Delete it
                # Use id if present, or name? API v1 uses user/tokens/{id} usually?
                # Or maybe we just use a different name to be safe?
                # Let's just create a unique name.
                pass

    # Create Token via API with unique name just in case
    import time

    token_name = f"test_token_{int(time.time())}"

    resp = requests.post(
        f"{API_URL}/users/{ADMIN_USER}/tokens",
        auth=auth,
        json={"name": token_name, "scopes": ["all"]},
    )

    if resp.status_code == 201:
        return resp.json()["sha1"]

    print(f"Token creation failed: {resp.status_code} - {resp.text}")
    # If fails (e.g. token exists), try list and delete or reuse?
    # For now, just fail or basic auth.
    return (ADMIN_USER, ADMIN_PASS)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws
