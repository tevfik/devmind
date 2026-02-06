import logging
import json
import re
import os
import git
from typing import Dict, Any, List, Optional
from langchain_core.output_parsers import JsonOutputParser

from agents.agent_base import (
    create_llm,
    print_section_header,
    print_success,
    print_warning,
    print_info,
    retrieve_relevant_context,
    Task,
)
from utils.prompts import TASK_SOLVER_PROMPT
from tools.analysis.build_analyzer import BuildAnalyzer
from tools.analysis.syntax import SyntaxChecker
from agents.agent_coder import CoderAgent
from agents.agent_reviewer import ReviewerAgent
from .utils import YaverClient

logger = logging.getLogger("agents.task_manager.executor")


class TaskExecutor:
    """Executes individual tasks."""

    def execute_task(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Execute a single task using LLM"""
        print_section_header(f"Executing task: {task.title}", "⚙️")

        llm = create_llm("code")

        # Prepare context string
        context_str = ""
        repo_path = "."

        if context.get("repo_info"):
            repo_info = context["repo_info"]
            if isinstance(repo_info, dict):
                repo_path = repo_info.get("repo_path", ".")
            else:
                repo_path = getattr(repo_info, "repo_path", ".")

            total_files = (
                getattr(repo_info, "total_files", 0)
                if not isinstance(repo_info, dict)
                else repo_info.get("total_files", 0)
            )
            languages = (
                getattr(repo_info, "languages", [])
                if not isinstance(repo_info, dict)
                else repo_info.get("languages", [])
            )
            context_str += f"Project Info: {total_files} files in {repo_path}\nLanguages: {languages}\n"

        # Add architecture context
        if context.get("architecture_analysis"):
            arch = context["architecture_analysis"]
            arch_type = (
                getattr(arch, "architecture_type", "unknown")
                if not isinstance(arch, dict)
                else arch.get("architecture_type", "unknown")
            )
            context_str += f"Architecture: {arch_type}\n"

        # Add dependency context (results of previous tasks)
        if task.dependencies and context.get("completed_tasks_results"):
            context_str += "\nDependency Results:\n"
            results = context.get("completed_tasks_results", {})
            for dep_id in task.dependencies:
                if dep_id in results:
                    context_str += f"- {dep_id}: {results[dep_id][:200]}...\n"

        # RAG Context retrieval
        rag_context = retrieve_relevant_context(
            f"{task.title}\n{task.description}", limit=3
        )
        if rag_context:
            context_str += f"\nRelevant Memory/Code:\n{rag_context}\n"

        # Build BuildAnalyzer info
        try:
            build_analyzer = BuildAnalyzer(repo_path)
            build_info = build_analyzer.analyze()
            files_mentioned = re.findall(
                r"\b[\w-]+\.\w+\b", task.title + " " + task.description
            )
            if files_mentioned:
                build_contexts = []
                for fname in files_mentioned:
                    if os.path.exists(os.path.join(repo_path, fname)):
                        b_ctx = build_analyzer.get_build_context_for_file(
                            os.path.join(repo_path, fname)
                        )
                        if b_ctx["build_type"] != "unknown":
                            build_contexts.append(f"{fname} -> {b_ctx['commands']}")
                if build_contexts:
                    context_str += (
                        "\n\nBuild Context (How to compile/test tasks):\n"
                        + "\n".join(build_contexts)
                        + "\n"
                    )

            if build_info:
                context_str += (
                    f"\nBuild System: {build_info.get('system', 'unknown')}\n"
                )
        except Exception as e:
            logger.warning(f"Build analysis failed: {e}")

        prompt = TASK_SOLVER_PROMPT
        print_info(f"Sending request to LLM (Model: {llm.model})...")

        chain = prompt | llm

        try:
            result = chain.invoke(
                {
                    "task_title": task.title,
                    "task_description": task.description,
                    "repo_context": context_str,
                    "context": "Follow the plan and implement changes.",
                }
            )
            response_content = (
                result.content if hasattr(result, "content") else str(result)
            )

            return {"success": True, "output": response_content}

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {"success": False, "error": str(e), "task_id": task.id}

    def apply_execution_side_effects(
        self, task: Task, result: Dict[str, Any], state: Optional[Dict] = None
    ):
        """
        Apply file changes and git operations from LLM execution result.
        """
        if not result or not result.get("success"):
            return

        output = result.get("output", "")
        client = YaverClient()

        # Determine repo path
        repo_path = None
        if hasattr(task, "repo_path") and task.repo_path:
            repo_path = task.repo_path
        elif state and state.get("repo_path"):
            repo_path = state.get("repo_path")
        elif state and state.get("repo_info"):
            repo_info = state.get("repo_info")
            if hasattr(repo_info, "repo_path"):
                repo_path = getattr(repo_info, "repo_path")
            elif isinstance(repo_info, dict) and "repo_path" in repo_info:
                repo_path = repo_info["repo_path"]

        if not repo_path:
            repo_path = "."
            logger.warning(f"No repo_path found, using current directory: {repo_path}")
        else:
            logger.info(f"Using repo_path: {repo_path}")

        repo = None
        is_pr_requested = False

        # 1. Detect Intent and Manage Branches (PRE-EMPTIVE)
        try:
            repo = git.Repo(repo_path)

            # Detect PR Intent (check task and original request)
            main_request = state.get("user_request", "").lower() if state else ""
            task_title_low = task.title.lower()
            task_desc_low = task.description.lower()

            # Check if this is a PR feedback task that should NOT create a new branch
            task_metadata = getattr(task, "metadata", {}) or {}
            should_skip_branch = task_metadata.get("skip_branch_creation", False)
            pr_branch = task_metadata.get("pr_branch")

            if should_skip_branch:
                logger.info(
                    f"Skipping branch creation for PR feedback task. Staying on current branch."
                )
                if pr_branch:
                    try:
                        current = repo.active_branch.name
                        if current != pr_branch:
                            logger.info(
                                f"Ensuring we're on PR branch: {pr_branch} (current: {current})"
                            )
                            repo.git.checkout(pr_branch)
                        else:
                            logger.info(f"Already on PR branch: {pr_branch}")
                    except Exception as e:
                        logger.warning(f"Failed to checkout PR branch {pr_branch}: {e}")
            else:
                # Original PR intent detection logic
                is_pr_requested = (
                    "pull request" in task_title_low
                    or "pull request" in task_desc_low
                    or "pull request" in main_request
                    or "pr" in task_title_low.split()
                    or "pr" in main_request.split()
                )
                logger.info(
                    f"PR Intent Detected: {is_pr_requested} (Title: '{task.title}', Main: '{main_request[:50]}...')"
                )

                if is_pr_requested:
                    new_branch_name = f"yaver-task-{task.id[:8]}"
                    if new_branch_name in repo.heads:
                        logger.info(
                            f"Feature branch {new_branch_name} already exists. Switching to it."
                        )
                        try:
                            repo.git.checkout(new_branch_name)
                            # Try to merge main in case it's behind
                            try:
                                logger.info(
                                    "Merging latest 'main' into feature branch..."
                                )
                                repo.git.pull("origin", "main", "--no-edit")
                            except Exception as merge_err:
                                logger.warning(
                                    f"Failed to auto-merge main: {merge_err}"
                                )
                        except Exception as checkout_err:
                            logger.warning(
                                f"Regular checkout failed, trying forced checkout: {checkout_err}"
                            )
                            repo.git.checkout("-f", new_branch_name)
                    else:
                        logger.info(f"Creating feature branch: {new_branch_name}")
                        new_branch = repo.create_head(new_branch_name)
                        new_branch.checkout()
        except Exception as git_pre_err:
            logger.warning(f"Git pre-emptive branching failed: {git_pre_err}")

        # 2. File extraction and writing
        # Regex to match ```language:filepath or ```filepath
        pattern = r"```(?:\w+)?(?::([^\n]+))?\n(.*?)```"
        matches = re.finditer(pattern, output, re.DOTALL)

        changes_applied = False
        applied_files = []

        for match in matches:
            file_path_raw = match.group(1)
            code = match.group(2)

            if not file_path_raw:
                continue

            file_path = file_path_raw.strip()
            if " " in file_path or "(" in file_path or "=" in file_path:
                continue

            # Safety check: avoid writing to root or directories as files
            if file_path in [".", "./", ""] or file_path.endswith("/"):
                logger.warning(f"Skipping invalid file path from LLM: '{file_path}'")
                continue

            full_path = os.path.join(repo_path, file_path)

            # Safety check: Is it an existing directory?
            if os.path.isdir(full_path):
                logger.warning(f"Skipping write to existing directory: '{file_path}'")
                continue

            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)

                # --- SYNTAX & AUTO-FIX LOOP ---
                try:
                    checker = SyntaxChecker()
                    syntax_result = checker.check(full_path)

                    if not syntax_result.valid:
                        error_msg = syntax_result.error_message
                        tool_used = syntax_result.tool_used
                        logger.warning(
                            f"⚠️ Syntax Error in {file_path} (via {tool_used}): {error_msg}"
                        )

                        client.add_comment(
                            task.id,
                            f"⚠️ Syntax Error detected ({tool_used}). Attempting auto-fix...\nError: {error_msg}",
                            author="SyntaxGuard",
                        )

                        # Attempt Fix (One-shot)
                        coder = CoderAgent()
                        fixed_response = coder.fix_code(
                            code, f"Compiler/Linter Error ({tool_used}): {error_msg}"
                        )

                        # Extract code from response
                        fix_match = re.search(
                            r"```(?:\w+)?\n(.*?)```", fixed_response, re.DOTALL
                        )
                        if fix_match:
                            new_code = fix_match.group(1)
                            with open(full_path, "w", encoding="utf-8") as f:
                                f.write(new_code)

                            # Re-verify
                            recheck = checker.check(full_path)
                            if recheck.valid:
                                logger.info(f"✅ Auto-fix successful for {file_path}")
                                client.add_comment(
                                    task.id,
                                    f"✅ Auto-fix successful for {file_path}.",
                                    author="SyntaxGuard",
                                )
                                # Update 'code' variable in case we use it later
                                code = new_code
                            else:
                                logger.warning(f"❌ Auto-fix failed for {file_path}")
                                client.add_comment(
                                    task.id,
                                    f"❌ Auto-fix failed. Remaining error: {recheck.error_message}",
                                    author="SyntaxGuard",
                                )
                        else:
                            logger.warning(
                                "Could not extract fixed code from agent response."
                            )

                except Exception as syntax_err:
                    logger.error(f"Syntax/Auto-fix logic failed: {syntax_err}")
                    # Don't stop the whole process, just log

                logger.info(f"Applied changes to {file_path}")
                changes_applied = True
                applied_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {e}")
                client.add_comment(
                    task.id,
                    f"❌ Failed to write file {file_path}: {e}",
                    author="Yaver Worker",
                )

        if applied_files:
            client.add_comment(
                task.id,
                f"📝 Modified files:\n- " + "\n- ".join(applied_files),
                author="Yaver Worker",
            )
            # Update state for commit
            if state is not None:
                if "staged_files" not in state:
                    state["staged_files"] = []
                state["staged_files"].extend(applied_files)

        # 3. Git Add (Staging)
        try:
            if repo and applied_files:
                repo.index.add(applied_files)
                logger.info(f"Staged {len(applied_files)} files")
        except Exception as e:
            logger.error(f"Failed to stage files: {e}")
