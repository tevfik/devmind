"""
Error Handling Utilities for Yaver AI
Provides graceful degradation when services are unavailable
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, cast

from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ServiceUnavailableError(Exception):
    """Raised when a required service is unavailable"""

    def __init__(self, service_name: str, message: Optional[str] = None):
        self.service_name = service_name
        self.message = message or f"{service_name} is unavailable"
        super().__init__(self.message)


def graceful_degradation(
    fallback_value: Any = None,
    service_name: str = "Service",
    log_error: bool = True,
):
    """
    Decorator for graceful degradation when services fail

    Args:
        fallback_value: Value to return on failure
        service_name: Name of the service for logging
        log_error: Whether to log the error

    Example:
        @graceful_degradation(fallback_value=[], service_name="Qdrant")
        def search_vectors(query):
            # This will return [] if Qdrant is unavailable
            return qdrant_client.search(query)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.warning(
                        f"{service_name} unavailable in {func.__name__}: {e}"
                    )
                    logger.debug(f"Returning fallback value: {fallback_value}")
                return cast(T, fallback_value)

        return wrapper

    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to retry a function on failure

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch

    Example:
        @retry_on_failure(max_retries=3, delay=1.0)
        def connect_to_service():
            return service.connect()
    """
    import time

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {current_delay}s delay"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Failed after {max_retries} retries: {func.__name__}"
                        )

            raise last_exception  # type: ignore

        return wrapper

    return decorator


def validate_service_available(
    service_name: str, check_func: Callable[[], bool]
) -> bool:
    """
    Validate if a service is available

    Args:
        service_name: Name of the service
        check_func: Function that returns True if service is available

    Returns:
        True if service is available, False otherwise
    """
    try:
        available = check_func()
        if available:
            logger.debug(f"{service_name} is available")
        else:
            logger.warning(f"{service_name} is not available")
        return available
    except Exception as e:
        logger.warning(f"Error checking {service_name} availability: {e}")
        return False
