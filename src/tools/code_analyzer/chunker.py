"""
Code Chunking Strategy

This module handles the logic of preparing code entities (functions, classes)
for embedding. It optimizes the text representation to improve retrieval quality.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from .models import FileAnalysis, FunctionInfo, ClassInfo

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a prepared chunk of code for embedding"""

    chunk_id: str
    text_content: str  # The optimized text to be embedded
    metadata: Dict[str, Any]
    original_source: str  # The actual code


class CodeChunker:
    """
    Splits file analysis results into semantic chunks.
    Uses context-aware strategies:
    - Include docstrings and signatures prominently.
    - Tag with file path and type.
    """

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens

    def chunk_file(
        self, file_analysis: FileAnalysis, source_code: str
    ) -> List[CodeChunk]:
        """
        Generate chunks from a file analysis object and its source.
        """
        chunks = []
        lines = source_code.splitlines()
        rel_path = file_analysis.file_path

        # 1. Chunk Functions
        for func in file_analysis.functions:
            chunk = self._create_function_chunk(func, lines, rel_path)
            if chunk:
                chunks.append(chunk)

        # 2. Chunk Classes (and their methods)
        for cls in file_analysis.classes:
            # Create a chunk for the class definition itself (docstring + init?)
            class_chunk = self._create_class_chunk(cls, lines, rel_path)
            if class_chunk:
                chunks.append(class_chunk)

            # Chunk methods
            for method in cls.methods:
                method_chunk = self._create_method_chunk(
                    method, cls.name, lines, rel_path
                )
                if method_chunk:
                    chunks.append(method_chunk)

        # 3. If no structural chunks found (e.g., non-Python or flat script)
        # OR if the file is handled by generic sliding window
        # Create sliding window chunks
        if not chunks and source_code.strip():
            sliding_chunks = self._create_sliding_window_chunks(
                source_code, rel_path, file_analysis.language
            )
            chunks.extend(sliding_chunks)

        return chunks

    def _create_sliding_window_chunks(
        self, source_code: str, rel_path: str, language: str
    ) -> List[CodeChunk]:
        """
        Splits generic text into overlapping chunks using a sliding window.
        Approx settings: 2000 chars window (~500 tokens), 400 chars overlap (~100 tokens).
        """
        chunks = []
        window_size = 2000
        overlap = 400

        # If small file, return single chunk
        if len(source_code) <= window_size:
            return [
                CodeChunk(
                    chunk_id=f"{rel_path}::whole",
                    text_content=f"File: {rel_path}\nType: File Content\nLanguage: {language}\n\n{source_code}",
                    metadata={
                        "id": f"{rel_path}::whole",
                        "file_path": rel_path,
                        "type": "file",
                        "name": rel_path.split("/")[-1],
                        "language": language,
                    },
                    original_source=source_code,
                )
            ]

        # Sliding Logic
        start = 0
        total_len = len(source_code)

        chunk_idx = 1
        while start < total_len:
            end = min(start + window_size, total_len)

            # Try to find a newline near the break point to avoid cutting lines in half
            if end < total_len:
                # Look for last newline within the last 100 chars of the window
                last_newline = source_code.rfind("\n", start, end)
                if last_newline != -1 and last_newline > (end - 100):
                    end = last_newline + 1  # Include the newline

            chunk_text = source_code[start:end]

            chunk_id = f"{rel_path}::part{chunk_idx}"
            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    text_content=f"File: {rel_path} (Part {chunk_idx})\nType: File Segment\nLanguage: {language}\n\n{chunk_text}",
                    metadata={
                        "id": chunk_id,
                        "file_path": rel_path,
                        "type": "file_segment",
                        "part": chunk_idx,
                        "name": rel_path.split("/")[-1],
                        "language": language,
                    },
                    original_source=chunk_text,
                )
            )

            if end >= total_len:
                break

            start += window_size - overlap
            chunk_idx += 1

        return chunks

    def _extract_source(self, start: int, end: int, lines: List[str]) -> str:
        """Extract lines 1-based inclusive"""
        if 0 < start <= len(lines) and 0 < end <= len(lines):
            return "\n".join(lines[start - 1 : end])
        return ""

    def _create_function_chunk(
        self, func: FunctionInfo, lines: List[str], file_path: str
    ) -> Optional[CodeChunk]:
        source = self._extract_source(func.start_line, func.end_line, lines)
        if not source.strip():
            return None

        # Construct optimized text representation
        # Format:
        # File: path/to/file.py
        # Type: Function
        # Name: my_func
        # Signature: def my_func(a, b) -> int
        # Docstring: ...
        # Code: ...

        signature = f"def {func.name}({', '.join(func.args)})"
        if func.returns:
            signature += f" -> {func.returns}"

        doc_part = f"\nDocstring: {func.docstring}" if func.docstring else ""

        # Limit code body length for embedding (keep start)
        # Aggressive truncation to avoid NaN errors from embedding model
        truncated_code = source[:800]  # Reduced to avoid problematic patterns

        text_content = (
            f"File: {file_path}\n"
            f"Type: Function\n"
            f"Name: {func.name}\n"
            f"Signature: {signature}"
            f"{doc_part}\n"
            f"Code:\n{truncated_code}"
        )

        return CodeChunk(
            chunk_id=f"{file_path}::{func.name}",
            text_content=text_content,
            metadata={
                "type": "function",
                "name": func.name,
                "file_path": file_path,
                "start_line": func.start_line,
                "end_line": func.end_line,
                "complexity": func.complexity,
            },
            original_source=source,
        )

    def _create_class_chunk(
        self, cls: ClassInfo, lines: List[str], file_path: str
    ) -> Optional[CodeChunk]:
        # For class, we extract definition but not ALL methods code, just signatures maybe?
        # Or just the class docstring and top level items.

        # Actually, let's just take the whole class text but verify size?
        # If class is huge, extracting just the top part (definition + docstring) is better.
        # Let's extract from start_line until first method start if possible, or just arbitrary.

        # For now, let takes the whole source but rely on 'text_content' formulation to focus on high level.
        source = self._extract_source(cls.start_line, cls.end_line, lines)
        if not source.strip():
            return None

        text_content = (
            f"File: {file_path}\n"
            f"Type: Class\n"
            f"Name: {cls.name}\n"
            f"Docstring: {cls.docstring or ''}\n"
            f"Bases: {', '.join(cls.bases)}\n"
        )

        return CodeChunk(
            chunk_id=f"{file_path}::{cls.name}",
            text_content=text_content,
            metadata={
                "type": "class",
                "name": cls.name,
                "file_path": file_path,
                "start_line": cls.start_line,
                "end_line": cls.end_line,
            },
            original_source=source,
        )

    def _create_method_chunk(
        self, method: FunctionInfo, class_name: str, lines: List[str], file_path: str
    ) -> Optional[CodeChunk]:
        source = self._extract_source(method.start_line, method.end_line, lines)
        if not source.strip():
            return None

        signature = f"def {method.name}({', '.join(method.args)})"
        doc_part = f"\nDocstring: {method.docstring}" if method.docstring else ""
        truncated_code = source[:2000]

        text_content = (
            f"File: {file_path}\n"
            f"Type: Method\n"
            f"Class: {class_name}\n"
            f"Name: {method.name}\n"
            f"Signature: {signature}"
            f"{doc_part}\n"
            f"Code:\n{truncated_code}"
        )

        return CodeChunk(
            chunk_id=f"{file_path}::{class_name}.{method.name}",
            text_content=text_content,
            metadata={
                "type": "method",
                "class": class_name,
                "name": method.name,
                "file_path": file_path,
                "start_line": method.start_line,
                "end_line": method.end_line,
            },
            original_source=source,
        )
