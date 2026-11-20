"""Logging setup for liuyao-kb.

Every log record passes through the redaction filter, so a credential that
accidentally reaches a log call is masked before it is written.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from liuyao_kb.config import redact


class RedactingFilter(logging.Filter):
    """Mask secret-looking content in every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        elif record.exc_info:
            import traceback

            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for the CLI."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # The neo4j driver logs connection URIs at DEBUG level.
    logging.getLogger("neo4j").setLevel(max(numeric_level, logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the redaction filter attached."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
    return logger


def safe(value: Any) -> str:
    """Render any value for display, with secrets masked."""
    return redact(str(value))
