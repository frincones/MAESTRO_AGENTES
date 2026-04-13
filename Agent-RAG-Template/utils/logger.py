"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys


def setup_logger(
    name: str = "agent-rag",
    level: str = "INFO",
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
) -> logging.Logger:
    """Configure and return a logger with console output."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)

    logger.propagate = False
    return logger


# Default application logger
app_logger = setup_logger()
