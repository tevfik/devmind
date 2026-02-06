from typing import List, Optional
from agents.agent_base import Task, TaskStatus, TaskPriority


class TaskScheduler:
    """Handles task scheduling logic."""

    def get_next_task(self, tasks: List[Task]) -> Optional[Task]:
        """Get next task to execute based on priorities and dependencies"""
        # Filter executable tasks (pending, no blocking dependencies)
        executable_tasks = []

        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            if task.dependencies:
                deps_completed = all(
                    any(
                        t.id == dep_id and t.status == TaskStatus.COMPLETED
                        for t in tasks
                    )
                    for dep_id in task.dependencies
                )
                if not deps_completed:
                    continue

            executable_tasks.append(task)

        if not executable_tasks:
            return None

        # Sort by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }

        executable_tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

        return executable_tasks[0]
