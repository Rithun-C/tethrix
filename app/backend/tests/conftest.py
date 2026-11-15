"""Shared test set-up."""

import json
import logging
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import Settings
from api.logs import JsonFormatter
from api.main import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings(log_level="INFO"))


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class _Collector(logging.Handler):
    """Keeps every log line exactly as it would be written, for tests to inspect."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(JsonFormatter())
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


LogReader = Callable[[], list[dict[str, Any]]]


@pytest.fixture
def raw_logs(app: FastAPI) -> Iterator[list[str]]:
    """The raw log lines written during a test. Depends on `app` so logging is set up."""
    collector = _Collector()
    root = logging.getLogger()
    root.addHandler(collector)
    try:
        yield collector.lines
    finally:
        root.removeHandler(collector)


@pytest.fixture
def logs(raw_logs: list[str]) -> LogReader:
    """The log lines, parsed from JSON."""
    return lambda: [json.loads(line) for line in raw_logs]
