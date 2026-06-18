"""
Module: utils/logger.py
Purpose: Structured JSON logging with PII scrubbing. Never logs tokens/PII.
Dependencies: stdlib logging, json, re
Author: ApplyPilot
"""
import json
import logging
import re
import sys

_SENSITIVE = ("password", "token", "access_token", "refresh_token", "authorization", "secret")

# Matches Bearer tokens and common key=value secret patterns in log message bodies.
# Groups: (prefix_including_equals_or_space)(secret_value)
_MSG_SECRET_RE: re.Pattern[str] = re.compile(
    r"(Bearer\s+)\S+"
    r"|((?:token|password|access_token|refresh_token|secret)=)\S+",
    re.IGNORECASE,
)


def _scrub_message(msg: str) -> str:
    """Replace secret values embedded in a log message string with ***.

    Redacts:
    - ``Bearer <token>`` → ``Bearer ***``
    - ``token=<value>``, ``password=<value>``, ``access_token=<value>``,
      ``refresh_token=<value>``, ``secret=<value>`` → ``<key>=***``

    Args:
        msg: The raw log message string.

    Returns:
        The message with secret portions replaced by ``***``.
    """

    def _replace(m: re.Match[str]) -> str:
        bearer_prefix = m.group(1)
        kv_prefix = m.group(2)
        if bearer_prefix is not None:
            return f"{bearer_prefix}***"
        return f"{kv_prefix}***"

    return _MSG_SECRET_RE.sub(_replace, msg)


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON with sensitive keys redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": _scrub_message(record.getMessage()),
        }
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = "***" if key.lower() in _SENSITIVE else value
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Return a configured JSON logger for the given name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
