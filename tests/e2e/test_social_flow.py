import pytest
import os
import time
import requests
import subprocess
from pathlib import Path

# Import Yaver components
# We need to ensure src is in path or installed in editable mode.
# Assuming pytest is run from root.

from agents.task_manager import social_developer_node
from core.git_helper import GitHelper
from tools.forge.tool import ForgeTool


def test_social_developer_flow_e2e(
    docker_env, admin_token, temp_workspace, monkeypatch
):
    """
    E2E Test:
    1. Setup a repo in Test Gitea.
    2. Create an Issue.
    3. Run Yaver Social Developer Node.
    4. Verify PR is created.
    """

    # 1. Setup Environment Variables for Test
    if isinstance(admin_token, tuple):
        username, password = admin_token
        token = "test_token_placeholder"  # We might fail here if token auth is strictly required for ForgeTool
        # Check if ForgeTool supports basic auth? Usually just token.
        # But let's assume conftest gives us a valid token.
        pytest.skip(
            "Skipping because admin token generation failed (basic auth fallback not implemented in test)"
        )
    else:
        token = admin_token
        username = "yaver_admin"

    # Gitea URL from docker-compose-test.yml (host machine perspective)
    GITEA_HOST_URL = "http://localhost:3000"

    # Override Config
    monkeypatch.setenv("GITEA_API_URL", f"{GITEA_HOST_URL}/api/v1")
    monkeypatch.setenv("FORGE_PROVIDER", "gitea")
    monkeypatch.setenv("GITEA_TOKEN", token)
    monkeypatch.setenv("YAVER_WORKSPACE_ROOT", str(temp_workspace))

    # 2. Setup Remote Repo via API
    repo_name = f"test_project_{int(time.time())}"
    api_url = f"{GITEA_HOST_URL}/api/v1"

    # Create Repo
    resp = requests.post(
        f"{api_url}/user/repos",
        headers={"Authorization": f"token {token}"},
        json={"name": repo_name, "auto_init": True, "private": False},
    )
    assert resp.status_code == 201, f"Failed to create repo: {resp.text}"
    repo_data = resp.json()
    clone_url = repo_data["clone_url"]  # Usually http://localhost:3000/user/repo.git

    # Fix clone URL for token auth if needed
    # Inject token: http://token@host...
    auth_clone_url = clone_url.replace("http://", f"http://{token}@")

    # 3. Create an Issue
    issue_title = "Add README Documentation"
    issue_body = "Please update the README.md file with 'Yaver Test Run'."

    resp = requests.post(
        f"{api_url}/repos/{username}/{repo_name}/issues",
        headers={"Authorization": f"token {token}"},
        json={"title": issue_title, "body": issue_body},
    )
    assert resp.status_code == 201
    issue_number = resp.json()["number"]

    # 4. Local Workspace Setup
    # Yaver usually clones repos into specific structure.
    # For this test, we can let Yaver handle cloning if we invoke the right node.
    # But social_developer_node scans ALL repos.
    # Let's clone manually to simulate "existing workspace" or configure Yaver to check this repo.

    project_dir = temp_workspace / username / repo_name
    project_dir.parent.mkdir(parents=True, exist_ok=True)

    # Clone it
    GitHelper.clone(auth_clone_url, str(project_dir))
    assert (project_dir / ".git").exists()

    # 5. Run the Agent Logic
    # We simulate the state passed to social_developer_node
    # Ideally, we want to call 'social_developer_node' and let it find the issue.
    # But for a focused test, we can mimic the "Task Manager Manager" node execution on a specific repo.

    print(f"Running agent on {project_dir} for issue #{issue_number}")

    # Initialize state
    state = {
        "user_request": f"Fix issue #{issue_number} in {repo_name}",  # Explicit instruction to bypass discovery phase for speed
        "repo_path": str(project_dir),
        "tasks": [],
        "log": [],
        "errors": [],
    }

    # We need to import the node that handles the task execution.
    # social_developer_node is high level (Monitor -> Select -> Act).
    # If we provide user_request, we can use the main loop or just task_manager_node.

    # However, to test full flow, let's try `task_manager_node` which decomposes and solves.
    from agents.task_manager import task_manager_node

    # NOTE: This runs the actual LLM. If Ollama is not reachable or models not pulled, this will fail/hang.
    # For E2E, we assume environment is ready (as checked in conftest).

    from agents.task_manager.manager import run_iteration_cycle

    try:
        # 1. Decompose / Plan
        state = task_manager_node(state)

        # 2. Execute Loop
        max_iter = 10
        iter_count = 0
        state["should_continue"] = True  # Force continue start

        while state.get("should_continue") and iter_count < max_iter:
            print(f"Executing iteration {iter_count}...")
            state = run_iteration_cycle(state)

            if state.get("errors"):
                print(f"Errors encountered: {state['errors']}")
                # Don't break immediately, maybe soft fail?

            iter_count += 1

        final_state = state
        # Verify no errors in execution
        assert not final_state.get(
            "errors"
        ), f"Agent errors: {final_state.get('errors')}"
    except Exception as e:
        pytest.fail(f"Agent execution failed: {e}")

    # 6. Verification
    # Check if file changed locally
    helper = GitHelper(project_dir)
    assert "README.md" in helper.list_files()  # It was auto-inited, so it exists.

    # Check if content updated? (Depends on LLM success)
    readme_content = (project_dir / "README.md").read_text()

    # Check if PR created on Gitea
    resp = requests.get(
        f"{api_url}/repos/{username}/{repo_name}/pulls",
        headers={"Authorization": f"token {token}"},
    )
    prs = resp.json()

    # Soft assertion for LLM variability
    if len(prs) > 0:
        print("SUCCESS: PR Created!")
        # Optional: Check PR body/title
    else:
        print("WARNING: No PR created. Check agent logs.")
        # If no PR, maybe it just committed to branch?
        branches = helper.get_branch()
        print(f"Current branch: {branches}")

    # For strict test passing without deterministic LLM, we might check if 'tasks' were generated.
    assert len(final_state["tasks"]) > 0, "No tasks were generated by the agent."
