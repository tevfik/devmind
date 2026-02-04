from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class MetricCalculator(ABC):
    """Abstract base class for metric calculators."""

    @abstractmethod
    def analyze(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a file and return metrics.

        Args:
            file_path: Path to the file to analyze.

        Returns:
            Dictionary containing metric names and values, or None if analysis fails.
        """
        pass
