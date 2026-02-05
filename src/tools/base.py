"""
Base Tool Interface
Result of Phase 2 Refactoring.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class Tool(ABC):
    """
    Abstract Base Class for all Yaver Tools.
    """

    name: str = "base_tool"
    description: str = "Base tool description"

    args_schema: Optional[type[BaseModel]] = None

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Execute the tool.
        """
        pass

    def to_langchain_tool(self):
        """
        Convert to LangChain compatible tool.
        """
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            func=self.run,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )
