import logging
import os
import shutil
from typing import Dict, Any, List

from agents.agent_base import (
    YaverState,
    Task,
    TaskStatus,
    TaskPriority,
    logger,
    print_section_header,
    print_success,
    print_warning,
    print_info,
    create_task_id,
    format_log_entry,
)
from config.config import get_config
from tools.forge.tool import ForgeTool
from tools.git.client import GitClient
from agents.agent_reviewer import ReviewerAgent

from .models import TaskDecomposition
from .decomposer import TaskDecomposer
from .scheduler import TaskScheduler
from .executor import TaskExecutor
from .utils import (
    YaverClient,
    update_task_status,
    commit_and_push_bundle,
)

# Instantiate components
decomposer = TaskDecomposer()
scheduler = TaskScheduler()
executor = TaskExecutor()


def run_iteration_cycle(state: YaverState) -> dict:
    """Run one iteration of task execution"""
    config = get_config()

    iteration_count = state.get("iteration_count", 0)
    tasks = state.get("tasks", [])

    if iteration_count >= config.task.max_iterations:
        print_warning(f"Max iterations reached: {config.task.max_iterations}")
        return {
            "should_continue": False,
            "log": state.get("log", [])
            + [format_log_entry("TaskManager", "Max iterations reached")],
        }

    # --- Reactive PR Monitoring ---
    active_pr = state.get("active_pr")
    repo_path = state.get("repo_path")

    # Proactive PR Detection
    if not active_pr and repo_path:
        try:
            from tools.git.ops import GitOps

            git_tool = GitOps(repo_path)
            if git_tool.repo:
                current_branch = git_tool.repo.active_branch.name
                if current_branch and current_branch != "main":
                    logger.info(
                        f"Proactively searching for PR for branch '{current_branch}'..."
                    )
                    forge = ForgeTool(repo_path=repo_path)
                    pr_info = forge.run(
                        "find_pr_by_branch", head=current_branch, base="main"
                    )
                    if isinstance(pr_info, dict) and "id" in pr_info:
                        active_pr = pr_info
                        state["active_pr"] = pr_info
                        logger.info(
                            f"Auto-detected active PR #{active_pr.get('number') or active_pr.get('id')} for monitoring."
                        )
        except Exception as detect_err:
            logger.warning(f"PR auto-detection failed: {detect_err}")

    if active_pr and isinstance(active_pr, dict):
        try:
            forge = ForgeTool(repo_path=repo_path)
            pr_id = active_pr.get("number") or active_pr.get("id")

            logger.info(f"Monitoring PR #{pr_id} for new feedback...")

            # 0. Get Agent Username
            agent_username = "yaver"
            try:
                user_info = forge.run("get_user")
                if isinstance(user_info, dict):
                    agent_username = (
                        user_info.get("login") or user_info.get("username") or "yaver"
                    )
            except Exception:
                pass

            # 1. Check PR status before processing
            pr_data = forge.run("get_pr", issue_id=pr_id)
            if isinstance(pr_data, dict) and pr_data.get("state") != "open":
                logger.info(
                    f"PR #{pr_id} is {pr_data.get('state')}. Skipping reactive loop."
                )
                return state

            # 2. Fetch comments
            comments = forge.run("list_comments", issue_id=pr_id)
            if isinstance(comments, list):
                if "processed_comment_ids" not in active_pr:
                    active_pr["processed_comment_ids"] = []

                # 3. Process NEW comments (excluding own)
                for comment in comments:
                    comment_id = comment.get("id")
                    comment_body = comment.get("body", "").strip()
                    user_info = comment.get("user", {})
                    username = user_info.get("login") or user_info.get("username")

                    # Ignore own comments and already processed ones
                    is_own_comment = username == agent_username
                    if os.environ.get("YAVER_SIMULATE_REVIEWER") == "1":
                        is_own_comment = False

                    if comment_id in active_pr["processed_comment_ids"]:
                        continue

                    if is_own_comment:
                        continue

                    logger.info(f"New PR feedback from {username}: {comment_body}")

                    # A. REACT (eyes emoji)
                    try:
                        forge.run("add_reaction", issue_id=comment_id, reaction="eyes")
                    except Exception as e:
                        logger.debug(f"Failed to add reaction: {e}")

                    # B. ACKNOWLEDGE
                    ack_msg = f"👀 I've seen your feedback: '{comment_body}'\n\nI'm starting to work on this now. I'll push the fixes shortly."
                    ack_comment = forge.run(
                        "comment_issue", issue_id=pr_id, body=ack_msg
                    )

                    if isinstance(ack_comment, dict) and "id" in ack_comment:
                        active_pr["processed_comment_ids"].append(ack_comment["id"])

                    # C. CREATE TASK
                    new_task_id = create_task_id()
                    # Check for conflict resolution request
                    is_conflict = any(
                        k in comment_body.lower()
                        for k in ["conflict", "merge", "çakışma", "kavga", "resolve"]
                    )

                    reactive_task = Task(
                        id=new_task_id,
                        title=f"{'Resolve Conflict' if is_conflict else 'Fix PR Feedback'}: {comment_body[:50]}...",
                        description=f"{'Resolve merge conflicts and ' if is_conflict else ''}Address reviewer feedback on PR #{pr_id}: {comment_body}",
                        priority=TaskPriority.HIGH,
                        status=TaskStatus.PENDING,
                        iteration=0,
                        originating_comment_id=comment_id,
                        metadata={
                            "is_pr_feedback": True,
                            "is_conflict_resolution": is_conflict,
                            "pr_id": pr_id,
                            "pr_branch": active_pr.get("head", {}).get("ref")
                            if isinstance(active_pr.get("head"), dict)
                            else None,
                            "skip_branch_creation": True,
                        },
                    )

                    tasks.append(reactive_task)
                    active_pr["processed_comment_ids"].append(comment_id)
                    logger.info(
                        f"Created reactive task {new_task_id} for comment {comment_id}"
                    )

        except Exception as e:
            logger.warning(f"PR monitoring failed: {e}")

    # Get next task
    next_task = scheduler.get_next_task(tasks)

    if not next_task:
        print_info("All tasks completed or blocked")

        # Ensure we commit any pending bundles if we are finishing up
        if state.get("staged_files"):
            try:
                repo_path = state.get("repo_path")
                commit_and_push_bundle(state, repo_path)
            except Exception as e:
                logger.error(f"Final commit bundle failed: {e}")

        state["should_continue"] = False
        state["log"] = state.get("log", []) + [
            format_log_entry("TaskManager", "No more tasks to execute")
        ]

        # Check for PR Conflict
        if state.get("active_pr"):
            active_pr = state["active_pr"]
            if active_pr.get("mergeable") is False:
                conflict_msg = f"⚠️ PR #{active_pr.get('number')} has merge conflicts that need manual resolution."
                logger.warning(conflict_msg)
                state["log"].append(format_log_entry("TaskManager", conflict_msg))

        return state

    # Update task status to in-progress
    next_task.status = TaskStatus.IN_PROGRESS
    next_task.iteration = iteration_count + 1

    # Execute task
    context = {
        "repo_info": state.get("repo_info"),
        "architecture_analysis": state.get("architecture_analysis"),
        "refactoring_plan": state.get("refactoring_plan"),
        "completed_tasks_results": {
            t.id: getattr(t, "result", "")
            for t in tasks
            if t.status == TaskStatus.COMPLETED
        },
    }

    # Pre-Execution Setup for Conflict Resolution
    task_metadata = getattr(next_task, "metadata", {}) or {}
    if task_metadata and task_metadata.get("is_conflict_resolution"):
        logger.info(
            f"🔧 Preparing environment for conflict resolution task {next_task.id}..."
        )
        try:
            import git

            repo_path = state.get("repo_path") or "."
            repo = git.Repo(repo_path)

            # Ensure we are on the PR branch
            pr_branch = task_metadata.get("pr_branch")
            if pr_branch:
                if repo.active_branch.name != pr_branch:
                    logger.info(
                        f"Switching to PR branch {pr_branch} for conflict resolution..."
                    )
                    repo.git.checkout(pr_branch)

            # Attemp merge to reproduce conflict markers
            try:
                target_branch = "origin/main"
                active_pr = state.get("active_pr")
                if active_pr:
                    base_info = active_pr.get("base", {})
                    if isinstance(base_info, dict) and base_info.get("ref"):
                        target_branch = f"origin/{base_info['ref']}"
                    elif hasattr(base_info, "ref"):
                        target_branch = f"origin/{base_info.ref}"

                logger.info(
                    f"Attempting merge with {target_branch} to reproduce conflicts..."
                )
                repo.git.fetch("origin")
                repo.git.merge(target_branch)
            except git.GitCommandError as e:
                if "conflict" in str(e).lower():
                    logger.info(
                        "✅ Conflict markers reproduced successfully. LLM will see them."
                    )
                else:
                    logger.warning(f"Merge failed with unexpected error: {e}")

        except Exception as e:
            logger.error(f"Failed to prepare conflict environment: {e}")

    execution_result = executor.execute_task(next_task, context)

    # Side Effects: Apply changes and Git Commit/Push
    executor.apply_execution_side_effects(next_task, execution_result, state)

    # Update task based on result
    if execution_result["success"]:
        tasks = update_task_status(
            tasks, next_task.id, TaskStatus.COMPLETED, result=execution_result["output"]
        )
    else:
        tasks = update_task_status(
            tasks, next_task.id, TaskStatus.FAILED, error=execution_result.get("error")
        )

    # Check if we should continue
    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

    should_continue = len(pending_tasks) > 0 or len(in_progress_tasks) > 0

    # Update state
    state["tasks"] = tasks
    state["current_task"] = next_task
    state["iteration_count"] = iteration_count + 1
    state["completed_tasks"] = state.get("completed_tasks", []) + (
        [next_task.id] if execution_result["success"] else []
    )
    state["should_continue"] = should_continue
    state["active_pr"] = active_pr

    new_log = [
        format_log_entry(
            "TaskManager",
            f"Iteration {iteration_count + 1}: Executed task {next_task.id}",
        ),
        format_log_entry(
            "TaskManager",
            f"Status: {'✅ Success' if execution_result['success'] else '❌ Failed'}",
        ),
    ]
    state["log"] = state.get("log", []) + new_log

    # Run final commit bundle if all tasks are completed
    if not should_continue and state.get("staged_files"):
        try:
            repo_path = state.get("repo_path")
            commit_and_push_bundle(state, repo_path)
        except Exception as e:
            logger.error(f"Final commit bundle failed: {e}")
            state["log"] = state.get("log", []) + [
                format_log_entry("TaskManager", f"❌ Bundle commit failed: {e}")
            ]

    return state


def task_manager_node(state: YaverState) -> dict:
    """Main task manager agent node"""
    logger.info("📋 Task Manager Agent started")

    user_request = state.get("user_request", "")

    if not user_request:
        error_msg = "User request not specified"
        return {
            "log": state.get("log", []) + [format_log_entry("TaskManager", error_msg)],
            "errors": state.get("errors", []) + [error_msg],
        }

    # Check if tasks already exist
    existing_tasks = state.get("tasks", [])

    if not existing_tasks:
        # Decompose task
        context = {
            "repo_info": state.get("repo_info"),
            "architecture_analysis": state.get("architecture_analysis"),
        }

        decomposition = decomposer.decompose(user_request, context)
        tasks = decomposer.create_tasks_from_decomposition(decomposition)

        print_success(f"✅ {len(tasks)} tasks created")

        state.update(
            {
                "tasks": tasks,
                "iteration_count": 0,
                "completed_tasks": [],
                "log": state.get("log", [])
                + [
                    format_log_entry("TaskManager", f"Created {len(tasks)} tasks"),
                    format_log_entry(
                        "TaskManager",
                        f"Complexity: {decomposition.estimated_complexity}",
                    ),
                ],
            }
        )
        return state
    else:
        # Run iteration
        return run_iteration_cycle(state)


def execute_specific_task(state: YaverState, task_data: dict) -> dict:
    """Execute a specific provided task"""
    # Convert dict to Task object if needed
    try:
        task = Task(**task_data) if isinstance(task_data, dict) else task_data
    except Exception as e:
        logger.error(f"Failed to parse task data: {e}")
        # dummy task wrapper
        task = Task(
            id=task_data.get("id", "unknown"),
            title=task_data.get("title", "Unknown Task"),
            description=task_data.get("description", ""),
            priority=TaskPriority.MEDIUM,
        )

    print_section_header(f"Executing Single Task: {task.title}", "🚀")

    context = {
        "repo_info": state.get("repo_info"),
        "architecture_analysis": state.get("architecture_analysis"),
        "file_analyses": state.get("file_analyses", []),
        "completed_tasks_results": {},
    }

    # Init API Client
    client = YaverClient()

    # Notify start
    client.add_comment(
        task.id,
        f"🚀 Task execution started via Python Worker\nPriority: {task.priority.value}",
        author="Yaver Worker",
    )

    # Execute task with LLM
    result = executor.execute_task(task, context)

    # Side Effects: Apply changes and Git Commit
    executor.apply_execution_side_effects(task, result, state)

    # Update status to CONTROL explicitly via client to ensure sync
    final_status = "control" if result["success"] else "failed"
    client.update_task_status(task.id, final_status)

    return {
        "task": task,
        "output": result.get("output", ""),
        "status": final_status,
        "result": result.get("output", ""),
    }


def social_developer_node(state: YaverState) -> dict:
    """
    Social Developer Agent Node.
    Monitors multiple repositories for activity and dispatches tasks.
    """
    logger.info("👀 Social Developer Agent monitoring...")

    try:
        forge = ForgeTool()
        repos = forge.run("list_repositories")
    except Exception as e:
        logger.warning(f"Failed to init ForgeTool: {e}")
        return state

    if not isinstance(repos, list):
        logger.warning(f"Failed to list repositories: {repos}")
        return state

    processed_any = False
    all_items = []

    # 1. Global Context First (Mentions) - Usually provider independent or global
    mentions = forge.run("list_mentions")
    if isinstance(mentions, list):
        all_items.extend([{"type": "mention", "data": m} for m in mentions])

    # 2. Iterate Repos for Context-Specific Items (Assignments, Review Requests)
    for repo in repos:
        repo_name = repo.get("name")
        repo_full_name = repo.get("full_name") or repo.get("name")
        owner_data = repo.get("owner", {})
        owner_login = owner_data.get("login") or owner_data.get("username")

        # Skip if necessary (e.g. forks, archived)
        if repo.get("archived"):
            continue

        logger.info(f"Checking {repo_full_name} for tasks...")

        # Switch Context
        try:
            forge.run("set_repo", owner=owner_login, repo=repo_name)
        except Exception as e:
            logger.warning(f"Failed to switch context to {repo_full_name}: {e}")
            continue

        # Check for Assignments & Reviews in THIS repo
        assigned = forge.run("list_assigned_issues")
        if isinstance(assigned, list):
            # Enrich data with repo context if missing
            for a in assigned:
                if "repository" not in a:
                    a["repository"] = repo
                all_items.append({"type": "assignment", "data": a})

        review_requests = forge.run("list_review_requests")
        if isinstance(review_requests, list):
            for r in review_requests:
                # Ensure we have repo context
                if "repository" not in r:
                    r["repository"] = repo
                # Also ensure basic PR fields
                if "base" not in r:  # Some list views might be summary only
                    # If we need details, we might fetch get_pr later
                    pass
                all_items.append({"type": "review_request", "data": r})

    if not all_items:
        logger.info("No active social tasks found.")
        return state

    # Deduplicate items by ID/Global ID to avoid processing same thing twice if API overlaps

    for item in all_items:
        item_type = item["type"]
        data = item["data"]

        # Determine Context
        repository = data.get("repository")

        # If review request, 'repository' might be missing in search results sometimes, check 'url'
        if not repository and "repository_url" in data:
            pass

        # MVP: Only process logic if we are "in" that repo or can switch to it.
        # But for 'social agent', we typically want to switch context.
        # Here we will just log and attempt local Review if it matches current dir

        issue_number = data.get("number")
        title = data.get("title")

        if item_type == "review_request":
            # Extract Repo Info from Item Data if available
            # In update above, we attached 'repository' object to data
            repo_info = data.get("repository", {})
            repo_full_name = repo_info.get("full_name") or repo_info.get("name")
            repo_ssh_url = repo_info.get("ssh_url") or repo_info.get("clone_url")

            logger.info(
                f"🔍 Found PR Review Request: #{issue_number} - {title} in {repo_full_name}"
            )

            # 1. Initialize Reviewer
            # We need to ensure we are in the correct directory for this repo
            # Determine local path
            workspace_dir = os.path.expanduser("~/.yaver/workspaces")
            local_repo_path = os.path.join(workspace_dir, repo_full_name)

            # Switch Forge Context to this repo for commenting
            owner = repo_info.get("owner", {}).get("login") or repo_info.get(
                "owner", {}
            ).get("username")
            name = repo_info.get("name")
            if owner and name:
                forge.run("set_repo", owner=owner, repo=name)

            # Clone if missing
            if not os.path.exists(local_repo_path):
                logger.info(f"Cloning {repo_full_name} to {local_repo_path}...")
                GitClient.clone(repo_ssh_url, local_repo_path)

            reviewer = ReviewerAgent(repo_path=local_repo_path)

            # 2. Checkout & Diff
            git = GitClient(local_repo_path)
            # Ensure we fetch the PR
            # checkout_pr handles fetching refs/pull/ID/head
            if git.checkout_pr(issue_number):
                # Diff from base (usually integration target like main/develop)
                base_branch = "main"
                if "base" in data:
                    base_ref = data["base"].get("ref")
                    if base_ref:
                        base_branch = base_ref

                # We need to make sure we have the base branch locally to diff against
                # Or use origin/base_branch
                try:
                    git.repo.remotes.origin.fetch()
                except:
                    pass

                # Diff against the base branch (remote)
                # If we use just "main", it might be local main which is old.
                # Safer to use origin/main if available
                target_base = f"origin/{base_branch}"

                diff_content = git.get_diff(target_base)

                if not diff_content:
                    # Fallback to local branch if origin ref missing
                    diff_content = git.get_diff(base_branch)

                if not diff_content:
                    logger.warning("Empty diff, skipping review.")
                    continue

                # 3. Analyze
                logger.info(f"Running automated review on PR #{issue_number}...")
                review_report = reviewer.review_code(
                    code=diff_content[:20000],  # Token limit safeguard
                    requirements="Review this Pull Request diff for security, bugs, and DORA metrics risks. Focus on the changes.",
                    file_path=f"PR #{issue_number}",
                )

                # 4. Post Feedback
                forge.run(
                    "comment_issue",
                    issue_id=issue_number,
                    body=f"## 🤖 Yaver Auto-Review\n\n{review_report}",
                )
                logger.info(f"Posted review to PR #{issue_number}")
                processed_any = True

            else:
                logger.error(f"Failed to checkout PR #{issue_number}")

        elif item_type == "mention":
            # Mentions (Notifications) have different structure
            subject = data.get("subject", {})
            title = subject.get("title")
            url = subject.get("url", "")
            try:
                issue_number = int(url.split("/")[-1])
            except (ValueError, IndexError):
                issue_number = None

            subject_type = subject.get("type")  # PullRequest or Issue

            repo_info = data.get("repository", {})
            repo_full_name = repo_info.get("full_name") or repo_info.get("name")
            repo_ssh_url = repo_info.get("ssh_url") or repo_info.get("clone_url")

            logger.info(f"🔔 Mentioned in {repo_full_name} #{issue_number}: {title}")

            if subject_type == "PullRequest" and issue_number:
                logger.info(
                    f"Mention is on a PR. Triggering auto-review for PR #{issue_number}..."
                )

                # 1. Initialize Reviewer Logic (Duplicated for robustness/independence)
                workspace_dir = os.path.expanduser("~/.yaver/workspaces")
                local_repo_path = os.path.join(workspace_dir, repo_full_name)

                # Switch Forge Context
                owner = repo_info.get("owner", {}).get("login") or repo_info.get(
                    "owner", {}
                ).get("username")
                name = repo_info.get("name")
                if owner and name:
                    forge.run("set_repo", owner=owner, repo=name)

                # Clone if missing
                if not os.path.exists(local_repo_path):
                    logger.info(f"Cloning {repo_full_name} to {local_repo_path}...")
                    GitClient.clone(repo_ssh_url, local_repo_path)

                reviewer = ReviewerAgent(repo_path=local_repo_path)

                # 2. Checkout & Diff
                git = GitClient(local_repo_path)
                if git.checkout_pr(issue_number):
                    base_branch = "main"
                    # Notifications don't give base branch info easily without fetching PR details
                    # We can try to fetch PR details
                    try:
                        pr_details = forge.run("get_pr", issue_id=issue_number)
                        if isinstance(pr_details, dict) and "base" in pr_details:
                            base_branch = pr_details["base"].get("ref", "main")
                    except Exception:
                        pass

                    try:
                        git.repo.remotes.origin.fetch()
                    except:
                        pass

                    target_base = f"origin/{base_branch}"
                    diff_content = git.get_diff(target_base)

                    if not diff_content:
                        diff_content = git.get_diff(base_branch)

                    if diff_content:
                        # 3. Analyze
                        logger.info(
                            f"Running automated review on PR #{issue_number} (Mention Trigger)..."
                        )
                        review_report = reviewer.review_code(
                            code=diff_content[:20000],
                            requirements="You were summoned via mention. Review this Pull Request diff for security, bugs, DORA metrics, and logical checks.",
                            file_path=f"PR #{issue_number}",
                        )

                        # 4. Post Feedback
                        forge.run(
                            "comment_issue",
                            issue_id=issue_number,
                            body=f"## 🤖 Yaver Auto-Review (Mentioned)\n\n{review_report}",
                        )
                        logger.info(
                            f"Posted mention-response review to PR #{issue_number}"
                        )
                        processed_any = True
                    else:
                        logger.warning("Empty diff, skipping review.")
                else:
                    logger.error(f"Failed to checkout PR #{issue_number}")
            else:
                logger.info(
                    "Mention is not on a PR (or ID missing). Skipping auto-review."
                )

    if not processed_any:
        logger.info("No new actionable items found.")

    return state
