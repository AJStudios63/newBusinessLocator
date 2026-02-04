"""
Centralized logging configuration for the newBusinessLocator ETL pipeline.

Provides a setup_logging() function to configure the Python logging module
with both console and file handlers.
"""

from __future__ import annotations

import logging

from config.settings import LOG_PATH

# Default log format
LOG_FORMAT: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str | int = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = False,
) -> logging.Logger:
    """
    Configure and return the root logger for the newBusinessLocator package.

    Parameters
    ----------
    level : str | int
        The logging level. Can be a string like 'DEBUG', 'INFO', 'WARNING',
        'ERROR', 'CRITICAL', or an int from the logging module.
    log_to_file : bool
        Whether to write logs to LOG_PATH (logs/pipeline.log).
    log_to_console : bool
        Whether to also output logs to stderr.

    Returns
    -------
    logging.Logger
        The configured logger instance for 'newBusinessLocator'.
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Get or create the package-level logger
    logger = logging.getLogger("newBusinessLocator")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # File handler
    if log_to_file:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            # If we can't write to the log file, fall back to console only
            import sys
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

    # Console handler (optional, for debugging)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Parameters
    ----------
    name : str | None
        The module name. If None, returns the root 'newBusinessLocator' logger.
        Otherwise returns 'newBusinessLocator.{name}'.

    Returns
    -------
    logging.Logger
        A logger instance.
    """
    if name is None:
        return logging.getLogger("newBusinessLocator")
    return logging.getLogger(f"newBusinessLocator.{name}")
