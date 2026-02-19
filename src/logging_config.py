"""
Logging configuration for the link organizer.
"""
import logging
import sys
from pathlib import Path


LOG_FILE = Path("link_organizer.log")


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root application logger.

    Logs go to both stderr (INFO+) and a rotating log file (DEBUG+).
    """
    logger = logging.getLogger("link_organizer")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO+)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (DEBUG+)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application root."""
    return logging.getLogger(f"link_organizer.{name}")
