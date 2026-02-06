import logging
from typing import List, Dict, Optional, Any
from langchain_core.output_parsers import JsonOutputParser

from agents.agent_base import (
    create_llm,
    print_section_header,
    print_info,
    print_success,
    retrieve_relevant_context,
    create_task_id,
    Task,
    TaskStatus,
    TaskPriority,
)
from config.config import get_config
from utils.prompts import DECOMPOSITION_PROMPT
from .models import TaskDecomposition

logger = logging.getLogger("agents.task_manager.decomposer")


class TaskDecomposer:
    """Handles task decomposition using LLM."""

    def decompose(
        self, user_request: str, context: Optional[Dict] = None
    ) -> TaskDecomposition:
        """Decompose user request into manageable subtasks using LLM"""
        print_section_header("Decomposing task", "📋")

        llm = create_llm("general", format="json")
        parser = JsonOutputParser(pydantic_object=TaskDecomposition)

        # 🧠 Memory Upgrade: Retrieve context from Qdrant/Neo4j
        memory_context = retrieve_relevant_context(user_request)

        context_str = ""
        if memory_context:
            context_str += memory_context
            print_info("Injected relevant memory context into planning")

        if context:
            if context.get("repo_info"):
                repo_info = context["repo_info"]
                # Support both object and dict
                total_files = (
                    getattr(repo_info, "total_files", 0)
                    if not isinstance(repo_info, dict)
                    else repo_info.get("total_files", 0)
                )
                total_lines = (
                    getattr(repo_info, "total_lines", 0)
                    if not isinstance(repo_info, dict)
                    else repo_info.get("total_lines", 0)
                )
                languages = (
                    getattr(repo_info, "languages", [])
                    if not isinstance(repo_info, dict)
                    else repo_info.get("languages", [])
                )

                context_str += f"\n\nProject Info:\n- File count: {total_files}\n- Total lines: {total_lines}\n- Languages: {languages}"

            if context.get("architecture_analysis"):
                arch = context["architecture_analysis"]
                arch_type = (
                    getattr(arch, "architecture_type", "unknown")
                    if not isinstance(arch, dict)
                    else arch.get("architecture_type", "unknown")
                )
                context_str += f"\n- Architecture: {arch_type}"

        prompt = DECOMPOSITION_PROMPT
        config = get_config()

        chain = prompt | llm | parser

        try:
            result = chain.invoke(
                {
                    "user_request": user_request,
                    "context": context_str,
                    "format_instructions": parser.get_format_instructions(),
                    "max_tasks": config.task.max_task_depth * 3,
                }
            )

            if not isinstance(result, dict):
                logger.error(
                    f"Invalid decomposition result format (not a dict): {result}"
                )
                # If it's a list, maybe it's the subtasks directly
                if isinstance(result, list):
                    result = {"subtasks": [str(s) for s in result]}
                else:
                    raise KeyError("subtasks")

            # Map 'tasks' to 'subtasks' if LLM hallucinated the key name
            if "tasks" in result and "subtasks" not in result:
                result["subtasks"] = [
                    t["title"] if isinstance(t, dict) and "title" in t else str(t)
                    for t in result["tasks"]
                ]

            # Handle case where it returned a single task object as the whole response
            if "title" in result and "subtasks" not in result:
                result["subtasks"] = [result["title"]]
                if "description" in result and "main_task" not in result:
                    result["main_task"] = result["description"]

            if "main_task" not in result:
                result["main_task"] = user_request

            if "subtasks" not in result or not isinstance(result["subtasks"], list):
                result["subtasks"] = [result.get("main_task") or user_request]

            if "priorities" not in result or not isinstance(result["priorities"], dict):
                result["priorities"] = {s: "medium" for s in result["subtasks"]}

            if "dependencies" not in result or not isinstance(
                result["dependencies"], dict
            ):
                result["dependencies"] = {}

            if "estimated_complexity" not in result:
                result["estimated_complexity"] = "medium"

            print_success(f"{len(result['subtasks'])} subtasks created")
            return TaskDecomposition(**result)

        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return TaskDecomposition(
                main_task=user_request,
                subtasks=[user_request],
                priorities={user_request: "high"},
                estimated_complexity="unknown",
                dependencies={},
            )

    def create_tasks_from_decomposition(
        self, decomposition: TaskDecomposition
    ) -> List[Task]:
        """Create Task objects from decomposition result"""
        tasks = []

        # Create main task
        main_task_id = create_task_id()
        main_task = Task(
            id=main_task_id,
            title=decomposition.main_task[:100],
            description=decomposition.main_task,
            priority=TaskPriority.HIGH,
            status=TaskStatus.IN_PROGRESS,
        )
        tasks.append(main_task)

        # Create subtasks
        subtask_ids = {}
        for i, subtask_desc in enumerate(decomposition.subtasks):
            task_id = create_task_id()

            # Determine priority
            priority_str = decomposition.priorities.get(subtask_desc, "medium")
            priority = (
                TaskPriority(priority_str)
                if priority_str in ["critical", "high", "medium", "low"]
                else TaskPriority.MEDIUM
            )

            task = Task(
                id=task_id,
                title=f"Subtask {i+1}: {subtask_desc[:80]}",
                description=subtask_desc,
                priority=priority,
                parent_task_id=main_task_id,
                status=TaskStatus.PENDING,
            )

            tasks.append(task)
            subtask_ids[subtask_desc] = task_id

        # Set dependencies
        for subtask_desc, deps in decomposition.dependencies.items():
            if subtask_desc in subtask_ids:
                task_id = subtask_ids[subtask_desc]
                task = next((t for t in tasks if t.id == task_id), None)
                if task:
                    task.dependencies = [
                        subtask_ids.get(dep, "") for dep in deps if dep in subtask_ids
                    ]

        # Update main task subtasks
        main_task.subtasks = [t.id for t in tasks if t.parent_task_id == main_task_id]

        return tasks
