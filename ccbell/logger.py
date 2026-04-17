"""
ccbell.logger — unified logging for ccbell.

Provides get_logger(name) that writes to both stderr and ~/.ccbell/ccbell.log.
All exceptions are silently swallowed; logging failures never propagate.

Input:  name (str) — logger name
Output: logging.Logger with stderr + file handlers
Usage:
    from ccbell.logger import get_logger
    log = get_logger("ccbell")
    log.info("hello")
Created: 2026-04-17
"""

import logging
import os
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_LOG_DIR = Path.home() / ".ccbell"


def get_logger(name: str) -> logging.Logger:
    """Return a logger with stderr and file handlers. Never raises."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(_LOG_FORMAT)

    # stderr handler
    try:
        sh = logging.StreamHandler()
        debug = os.environ.get("CCBELL_DEBUG", "") == "1"
        sh.setLevel(logging.DEBUG if debug else logging.INFO)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    except Exception:
        pass

    # file handler
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(_LOG_DIR / "ccbell.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

    return logger
