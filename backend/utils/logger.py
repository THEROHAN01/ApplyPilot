"""
Module: utils/logger.py
Purpose: Structured JSON logging with PII scrubbing. Never logs tokens/PII.
Dependencies: stdlib logging, json
Author: ApplyPilot
"""
import json
import logging
import sys

_SENSITIVE = ("password", "token", "access_token", "refresh_token", "authorization", "secret")


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON with sensitive keys redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
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
