import logging
import lizard
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from .base import MetricCalculator

logger = logging.getLogger(__name__)


class PythonComplexityAnalyzer(MetricCalculator):
    def analyze(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze Python file complexity using radon"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            complexity_results = cc_visit(code)
            avg_complexity = (
                sum(r.complexity for r in complexity_results) / len(complexity_results)
                if complexity_results
                else 0
            )
            max_complexity = max((r.complexity for r in complexity_results), default=0)

            # maintainability index
            mi_results = mi_visit(code, True)
            maintainability = (
                float(mi_results) if isinstance(mi_results, (int, float)) else 0.0
            )

            return {
                "avg_complexity": round(avg_complexity, 2),
                "max_complexity": max_complexity,
                "maintainability_index": round(maintainability, 2),
                "complex_functions": [
                    {
                        "name": r.name,
                        "complexity": r.complexity,
                        "lineno": getattr(r, "lineno", 0),
                    }
                    for r in complexity_results
                    if r.complexity > 10
                ],
                "tool": "radon",
            }
        except Exception as e:
            logger.debug(f"Radon complexity analysis failed for {file_path}: {e}")
            return None


class GenericComplexityAnalyzer(MetricCalculator):
    def analyze(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze file using Lizard (C++, Java, JS, etc.)"""
        try:
            analysis = lizard.analyze_file(str(file_path))
            if not analysis:
                return None

            return {
                "avg_complexity": round(
                    float(analysis.average_cyclomatic_complexity), 2
                ),
                "max_complexity": max(
                    (f.cyclomatic_complexity for f in analysis.function_list), default=0
                ),
                "maintainability_index": None,  # Lizard doesn't provide MI easily
                "nloc": analysis.nloc,
                "complex_functions": [
                    {
                        "name": f.name,
                        "complexity": f.cyclomatic_complexity,
                        "lineno": f.start_line,
                    }
                    for f in analysis.function_list
                    if f.cyclomatic_complexity > 10
                ],
                "tool": "lizard",
            }
        except Exception as e:
            logger.debug(f"Lizard complexity analysis failed for {file_path}: {e}")
            return None


def count_lines_of_code(file_path: Path) -> Tuple[int, int, int]:
    """
    Count total lines, code lines, and comment lines.
    Returns: (total_lines, code_lines, comment_lines)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        blank = sum(1 for line in lines if line.strip() == "")

        # Simple comment detection
        comments = 0
        for line in lines:
            stripped = line.strip()
            # Basic heuristics for comments in common languages
            if (
                stripped.startswith("#")
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                or stripped.startswith("--")  # SQL/Lua
                or stripped.startswith("%")  # LaTeX/Erlang
            ):
                comments += 1

        code = total - blank - comments
        return total, code, comments
    except Exception as e:
        logger.warning(f"Could not count lines for {file_path}: {e}")
        return 0, 0, 0


class MetricsManager:
    """Factory to get appropriate analyzer"""

    def __init__(self):
        self.py_analyzer = PythonComplexityAnalyzer()
        self.gen_analyzer = GenericComplexityAnalyzer()

    def get_metrics(self, file_path: Path) -> Dict[str, Any]:
        """
        Get all available metrics for a file.
        Detects language and chooses best tool.
        """
        metrics = {"complexity": None, "lines": {"total": 0, "code": 0, "comments": 0}}

        # 1. Line Counts
        total, code, comments = count_lines_of_code(file_path)
        metrics["lines"] = {"total": total, "code": code, "comments": comments}

        # 2. Complexity
        if file_path.suffix == ".py":
            # Prefer Radon for Python
            metrics["complexity"] = self.py_analyzer.analyze(file_path)

        # Fallback to Lizard if Radon failed or not Python
        if not metrics["complexity"]:
            metrics["complexity"] = self.gen_analyzer.analyze(file_path)

        return metrics
