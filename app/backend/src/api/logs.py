"""Structured logs: every log line is one JSON object.

Why JSON: CloudWatch Logs can filter and search on JSON fields, for example "all
requests with status 500" or "everything with this request ID".

Rule (SR-42, SR-44): request bodies, response bodies, headers and tokens are never
logged. Callers pass named fields through `extra={...}`; nothing else gets in.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# The attributes every LogRecord has. Anything else on a record came from `extra=`.
_STANDARD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "taskName",
    "color_message",  # uvicorn's copy of the message with terminal colour codes
}


class JsonFormatter(logging.Formatter):
    """Turns a log record into one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                line[key] = value
        # Deliberately no traceback text here: an exception message can contain user
        # data. The request middleware logs the error type and code locations instead.
        return json.dumps(line, default=str)


def setup_logging(level: str) -> None:
    """Send every logger's output through the JSON formatter, to standard output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn installs its own plain-text handlers. Remove them so its messages (start,
    # stop, errors) come out as JSON too.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    # Libraries that make HTTP calls log the full address, query string included, and
    # the AWS SDK logs request details at DEBUG. Keep them to warnings (SR-42).
    for name in ("boto3", "botocore", "urllib3", "httpx", "httpx2"):
        logging.getLogger(name).setLevel(logging.WARNING)
