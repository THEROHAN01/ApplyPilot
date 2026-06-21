"""Tests for message-body token scrubbing in utils/logger.py."""
import json
import logging
from io import StringIO

from utils.logger import JsonFormatter, _scrub_message


def _capture_log(message: str) -> dict:
    """Emit *message* through a JsonFormatter and return the parsed JSON payload.

    Args:
        message: The log message string to emit.

    Returns:
        Parsed JSON dict produced by JsonFormatter.
    """
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(f"test_logger.{id(message)}")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info(message)
    return json.loads(buf.getvalue())


class TestScrubMessage:
    """Unit tests for the _scrub_message helper."""

    def test_bearer_token_is_redacted(self) -> None:
        result = _scrub_message("user logged in with Bearer abc123secret")
        assert "abc123secret" not in result
        assert "Bearer ***" in result

    def test_bearer_case_insensitive(self) -> None:
        result = _scrub_message("auth header: bearer MyS3cr3tT0k3n")
        assert "MyS3cr3tT0k3n" not in result
        assert "***" in result

    def test_token_equals_is_redacted(self) -> None:
        result = _scrub_message("request token=abc123")
        assert "abc123" not in result
        assert "token=***" in result

    def test_password_equals_is_redacted(self) -> None:
        result = _scrub_message("binding password=hunter2 failed")
        assert "hunter2" not in result
        assert "password=***" in result

    def test_access_token_equals_is_redacted(self) -> None:
        result = _scrub_message("access_token=ACCESSSECRET stored")
        assert "ACCESSSECRET" not in result
        assert "access_token=***" in result

    def test_refresh_token_equals_is_redacted(self) -> None:
        result = _scrub_message("refresh_token=REFRESHSECRET rotated")
        assert "REFRESHSECRET" not in result
        assert "refresh_token=***" in result

    def test_secret_equals_is_redacted(self) -> None:
        result = _scrub_message("secret=topsecretvalue in config")
        assert "topsecretvalue" not in result
        assert "secret=***" in result

    def test_non_sensitive_text_preserved(self) -> None:
        msg = "user john.doe@example.com signed up successfully"
        result = _scrub_message(msg)
        assert result == msg

    def test_empty_message_unchanged(self) -> None:
        assert _scrub_message("") == ""


class TestJsonFormatterScrubbing:
    """Integration tests: scrubbing runs through the full JsonFormatter pipeline."""

    def test_bearer_redacted_in_formatted_output(self) -> None:
        payload = _capture_log("user logged in with Bearer abc123secret")
        assert "abc123secret" not in payload["msg"]
        assert "Bearer ***" in payload["msg"]

    def test_token_equals_redacted_in_formatted_output(self) -> None:
        payload = _capture_log("token=abc123")
        assert "abc123" not in payload["msg"]
        assert "token=***" in payload["msg"]

    def test_non_sensitive_text_preserved_in_formatted_output(self) -> None:
        msg = "application submitted for job_id=42"
        payload = _capture_log(msg)
        assert payload["msg"] == msg

    def test_extra_fields_sensitive_key_still_redacted(self) -> None:
        """extra_fields redaction must not be broken by the new scrub pass."""
        buf = StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("test_logger.extra_fields")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        record = logger.makeRecord(
            name=logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg="plain message",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"token": "supersecret", "user_id": "u-999"}  # type: ignore[attr-defined]
        handler.emit(record)

        payload = json.loads(buf.getvalue())
        assert payload["token"] == "***"
        assert payload["user_id"] == "u-999"
        assert payload["msg"] == "plain message"
