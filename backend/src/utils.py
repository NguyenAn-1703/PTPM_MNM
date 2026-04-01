"""Common helper utilities for scripts and diagnostics."""
from contextlib import contextmanager
import logging
import time
from typing import Iterator


logger = logging.getLogger(__name__)


@contextmanager
def timed(label: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - started) * 1000
        logger.info("%s took %.2f ms", label, elapsed)
