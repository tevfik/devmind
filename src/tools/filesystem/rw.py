"""
Filesystem Tools
"""

import os
from pathlib import Path
from typing import Any, Dict
from tools.base import Tool


class FileReadTool(Tool):
    name = "file_read"
    description = "Read file content"

    def run(self, path: str, **kwargs) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {path}: {e}"


class FileWriteTool(Tool):
    name = "file_write"
    description = "Write content to file (overwrite)"

    def run(self, path: str, content: str, **kwargs) -> Any:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing to {path}: {e}"


class FileEditTool(Tool):
    name = "file_edit"
    description = "Replace string in file"

    def run(self, path: str, old_text: str, new_text: str, **kwargs) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_text not in content:
                return f"Error: '{old_text}' not found in {path}"

            new_content = content.replace(old_text, new_text)

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Successfully replaced text in {path}"
        except Exception as e:
            return f"Error editing {path}: {e}"
