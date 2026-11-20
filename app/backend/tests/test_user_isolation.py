"""Integration test: one user's query never returns another user's items.

Needs DynamoDB Local, which Docker Compose starts. It uses its own table, so the data
you see in the running app is not touched.

This is the first piece of the two-user IDOR harness (T-013). B4 builds on it with
real endpoints and tokens.
"""

import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from boto3.dynamodb.conditions import Key

from api.config import Settings, get_settings
from api.db import GSI1, DynamoProfileStore, dynamodb_resource, user_pk
from local_table import create_table, wait_until_ready
from seed import ALICE, BOB, seed

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def table() -> Iterator["Table"]:
    settings: Settings = get_settings()
    if settings.dynamodb_endpoint_url is None:
        pytest.skip("DYNAMODB_ENDPOINT_URL is not set: DynamoDB Local is not available")

    dynamodb = dynamodb_resource(settings)
    wait_until_ready(dynamodb)
    name = f"test-{uuid.uuid4().hex[:12]}"
    create_table(dynamodb, name)
    test_table = dynamodb.Table(name)
    seed(test_table)
    try:
        yield test_table
    finally:
        test_table.delete()


def test_seed_wrote_both_users(table: "Table") -> None:
    assert table.scan()["Count"] == 7


def test_partition_query_returns_only_that_user(table: "Table") -> None:
    items = table.query(KeyConditionExpression=Key("PK").eq(user_pk(ALICE)))["Items"]

    assert len(items) == 4
    assert {item["PK"] for item in items} == {user_pk(ALICE)}
    assert not any("Bob" in str(item.get("title", "")) for item in items)


def test_open_todos_index_returns_only_that_user(table: "Table") -> None:
    items = table.query(
        IndexName=GSI1,
        KeyConditionExpression=Key("GSI1PK").eq(f"{user_pk(BOB)}#TODO#OPEN"),
    )["Items"]

    assert sorted(str(item["title"]) for item in items) == [
        "Bob: book the dentist",
        "Bob: clean the bike",
    ]


def test_dated_todos_sort_before_undated_ones(table: "Table") -> None:
    items = table.query(
        IndexName=GSI1,
        KeyConditionExpression=Key("GSI1PK").eq(f"{user_pk(ALICE)}#TODO#OPEN"),
    )["Items"]

    assert [item["SK"] for item in items] == ["TODO#a1", "TODO#a2"]


def test_index_does_not_copy_fields_it_should_not(table: "Table") -> None:
    items = table.query(
        IndexName=GSI1,
        KeyConditionExpression=Key("GSI1PK").eq(f"{user_pk(ALICE)}#TODO#DONE"),
    )["Items"]

    assert len(items) == 1
    assert "completedAt" not in items[0]
    assert items[0]["title"] == "Alice: pay the electricity bill"


def test_profile_store_reads_only_the_asked_users_profile(table: "Table") -> None:
    # The store auth_gate uses (SR-03), against the real table shape.
    profiles = DynamoProfileStore(table)

    alice = profiles.get(ALICE)
    assert alice is not None
    assert alice["PK"] == user_pk(ALICE)
    assert alice["timeZone"] == "Asia/Kolkata"
    assert profiles.get("nobody") is None
