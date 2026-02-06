"""
Performance Metrics Tracking for Yaver AI
Simple metrics collection for monitoring system performance
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import statistics

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Metric:
    """Single metric measurement"""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Simple in-memory metrics collector"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)

        # Keep only last 1000 measurements
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]

    def increment(self, name: str, value: int = 1):
        """Increment a counter"""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value

    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return None

        values = self.metrics[name]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self.counters.get(name, 0)

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get all metric statistics"""
        return {
            name: self.get_stats(name) for name in self.metrics if self.get_stats(name)
        }

    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()


# Global metrics collector
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics


class Timer:
    """Context manager for timing operations"""

    def __init__(self, name: str, log: bool = False):
        self.name = name
        self.log = log
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        _metrics.record(self.name, self.elapsed)

        if self.log:
            logger.info(f"{self.name} took {self.elapsed:.3f}s")


def track_performance(metric_name: str):
    """
    Decorator to track function execution time

    Example:
        @track_performance("code_analysis")
        def analyze_code(path):
            # Function execution time will be tracked
            pass
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with Timer(metric_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
