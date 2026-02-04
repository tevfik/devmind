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

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Execute the tool.
        """
        pass

    def to_langchain_tool(self):
        """
        Convert to LangChain compatible tool.
        (Optional, for future integration)
        """
        from langchain_core.tools import Tool as LangChainTool

        return LangChainTool(
            name=self.name, func=self.run, description=self.description
        )
