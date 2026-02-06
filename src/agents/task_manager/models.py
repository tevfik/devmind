from typing import List, Dict, Any
from pydantic import BaseModel, Field
from agents.agent_base import Task, TaskStatus, TaskPriority


class TaskDecomposition(BaseModel):
    """Task decomposition result"""

    main_task: str = Field(description="Main task description")
    subtasks: List[str] = Field(description="List of subtasks")
    priorities: Dict[str, Any] = Field(
        default_factory=dict, description="Priority for each subtask"
    )
    dependencies: Dict[str, Any] = Field(
        default_factory=dict, description="Dependencies between tasks"
    )
    estimated_complexity: str = Field(description="Overall complexity: low/medium/high")


__all__ = ["Task", "TaskStatus", "TaskPriority", "TaskDecomposition"]
