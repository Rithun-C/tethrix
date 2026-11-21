"""Shared test set-up."""

import json
import logging
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import Settings, get_settings
from api.db import dynamodb_resource
from api.logs import JsonFormatter
from api.main import create_app
from api.todos import DynamoTodoStore
from local_table import create_table, wait_until_ready
from tests.auth_helpers import bearer, install_test_auth, make_token

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table


@pytest.fixture
def app() -> FastAPI:
    test_app = create_app(Settings(log_level="INFO"))
    install_test_auth(test_app)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Not signed in."""
    return TestClient(app)


@pytest.fixture
def alice(app: FastAPI) -> TestClient:
    """Signed in as alice (B4-04: the two-user harness)."""
    return TestClient(app, headers=bearer(make_token("alice")))


@pytest.fixture
def bob(app: FastAPI) -> TestClient:
    """Signed in as bob."""
    return TestClient(app, headers=bearer(make_token("bob")))


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


# ---- Database and clock (B5) -------------------------------------------------------


class FakeClock:
    """The app's clock, set by the test. Starts at 2026-11-22 06:00 UTC."""

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 22, 6, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock(app: FastAPI) -> FakeClock:
    fake = FakeClock()
    app.state.clock = fake
    return fake


@pytest.fixture(scope="session")
def dynamo_table() -> Iterator["Table"]:
    """A table of its own in DynamoDB Local for the whole test run, deleted at the end.
    The data in the running app is never touched."""
    settings = get_settings()
    if settings.dynamodb_endpoint_url is None:
        pytest.skip("DYNAMODB_ENDPOINT_URL is not set: DynamoDB Local is not available")
    dynamodb = dynamodb_resource(settings)
    wait_until_ready(dynamodb)
    name = f"test-{uuid.uuid4().hex[:12]}"
    create_table(dynamodb, name)
    table = dynamodb.Table(name)
    try:
        yield table
    finally:
        table.delete()


@pytest.fixture
def todo_table(dynamo_table: "Table") -> "Table":
    """The test table, emptied before each test."""
    scan: dict[str, Any] = {"ProjectionExpression": "PK, SK"}
    while True:
        page = dynamo_table.scan(**scan)
        with dynamo_table.batch_writer() as batch:
            for item in page["Items"]:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        if "LastEvaluatedKey" not in page:
            break
        scan["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return dynamo_table


@pytest.fixture
def todos_db(app: FastAPI, todo_table: "Table", clock: FakeClock) -> "Table":
    """Points the app's todos at the empty test table, with the fake clock."""
    app.state.todos = DynamoTodoStore(todo_table)
    return todo_table
