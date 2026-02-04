"""
Code Parser Module
Extracted from git_analysis.py
"""

import ast
from pathlib import Path
from typing import Dict, Any, List
import re


class CodeParser:
    """Parses code to extract structural information (AST-based + Regex fallback)."""

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a file to extract functions, classes, and calls."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".py":
            return self._parse_python(path)
        elif suffix in [
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".java",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
        ]:
            return self._parse_generic_regex(path)
        else:
            return {"error": "Unsupported file type"}

    def _parse_python(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            tree = ast.parse(content)

            functions = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ]
            classes = [
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            imports = [
                node.names[0].name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
            ]
            imports += [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            ]

            # Extract calls
            calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    caller_name = node.name
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            func = child.func
                            callee_name = None
                            if isinstance(func, ast.Name):
                                callee_name = func.id
                            elif isinstance(func, ast.Attribute):
                                callee_name = func.attr

                            if callee_name:
                                calls.append(
                                    {"caller": caller_name, "callee": callee_name}
                                )

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(content.splitlines()),
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_generic_regex(self, path: Path) -> Dict[str, Any]:
        """Simple regex based parser for C-like languages."""

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Simple C-function regex: Type Name(Args) {
            # Limiting to common C patterns to avoid false positives
            # Improved regex to handle pointers and attributes better
            func_pattern = re.compile(r"^\s*(?:[\w\*]+\s+)+(\w+)\s*\(", re.MULTILINE)
            raw_functions = func_pattern.findall(content)

            # Filter out control structures that look like function definitions (e.g. "else if")
            # We allow 'main' because it's a critical entry point function
            blacklist = {
                "if",
                "while",
                "switch",
                "for",
                "catch",
                "return",
                "sizeof",
                "else",
                "define",
            }
            functions = [f for f in raw_functions if f not in blacklist]

            # Classes (for C++/Java)
            class_pattern = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
            classes = class_pattern.findall(content)

            # Includes/Imports
            imports = []
            include_pattern = re.compile(r'#include\s+[<"](.+)[>"]')
            imports.extend(include_pattern.findall(content))

            # Calls - this is hard with detailed scope parsing using just regex.
            calls = []
            current_func = None

            lines = content.splitlines()
            for line in lines:
                # Check for function start
                func_match = func_pattern.search(line)
                if func_match and "{" in line:  # Basic heuristics
                    current_func = func_match.group(1)
                    continue

                if current_func:
                    # Look for calls:  func_name(
                    call_matches = re.findall(r"(\w+)\s*\(", line)
                    for callee in call_matches:
                        if callee not in blacklist and callee != current_func:
                            calls.append({"caller": current_func, "callee": callee})

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(lines),
            }
        except Exception as e:
            return {"error": str(e)}
