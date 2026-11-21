"""Todos API behaviour against DynamoDB Local (B5-01, B5-02; US-10 to US-13).

Input rules are in test_todos_validation.py; the two-user tests are in test_idor.py.
"""

import base64
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeClock

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("todos_db")]

TODOS = "/api/v1/todos"


def add(client: TestClient, title: str, **fields: Any) -> dict[str, Any]:
    response = client.post(TODOS, json={"title": title, **fields})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def titles(client: TestClient, view: str) -> list[str]:
    response = client.get(TODOS, params={"view": view})
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


# ---- US-10: add ------------------------------------------------------------------


def test_add_returns_the_new_todo(alice: TestClient) -> None:
    todo = add(
        alice, "  Pay the bill  ", notes="Before Friday", dueDate="2026-11-25", priority="high"
    )

    assert todo == {
        "todoId": todo["todoId"],
        "title": "Pay the bill",  # trimmed
        "notes": "Before Friday",
        "dueDate": "2026-11-25",
        "priority": "high",
        "completed": False,
        "completedAt": None,
        "createdAt": "2026-11-22T06:00:00.000Z",
        "updatedAt": "2026-11-22T06:00:00.000Z",
    }
    assert len(todo["todoId"]) == 26


def test_ids_sort_in_creation_order(alice: TestClient, clock: FakeClock) -> None:
    first = add(alice, "first")
    clock.now = datetime(2026, 11, 22, 6, 0, 1, tzinfo=UTC)
    second = add(alice, "second")

    assert first["todoId"] < second["todoId"]


def test_the_item_is_stored_under_the_users_partition(alice: TestClient, todos_db: "Table") -> None:
    todo = add(alice, "Stored")

    item = todos_db.get_item(Key={"PK": "USER#alice", "SK": f"TODO#{todo['todoId']}"})["Item"]
    assert item["GSI1PK"] == "USER#alice#TODO#OPEN"
    assert item["GSI1SK"] == f"NODUE#{todo['todoId']}"
    assert "notes" not in item  # empty optional fields are left off


def test_get_returns_the_notes(alice: TestClient) -> None:
    todo = add(alice, "With notes", notes="line one\nline two")

    response = alice.get(f"{TODOS}/{todo['todoId']}")

    assert response.status_code == 200
    assert response.json()["notes"] == "line one\nline two"


# ---- US-11: tick and untick -------------------------------------------------------


def test_tick_moves_a_todo_to_completed_and_records_when(
    alice: TestClient, clock: FakeClock
) -> None:
    todo = add(alice, "Tick me", dueDate="2026-11-22")
    clock.now = datetime(2026, 11, 22, 7, 30, tzinfo=UTC)

    response = alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": True})

    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert response.json()["completedAt"] == "2026-11-22T07:30:00.000Z"
    assert titles(alice, "today") == []
    completed = alice.get(TODOS, params={"view": "completed"}).json()["items"]
    assert completed == [
        {
            "todoId": todo["todoId"],
            "title": "Tick me",
            "dueDate": "2026-11-22",
            "priority": None,
            "completed": True,
            "completedAt": "2026-11-22T07:30:00.000Z",
        }
    ]


def test_untick_moves_it_back(alice: TestClient) -> None:
    todo = add(alice, "Oops", dueDate="2026-11-22")
    alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": True})

    response = alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": False})

    assert response.json()["completed"] is False
    assert response.json()["completedAt"] is None
    assert titles(alice, "today") == ["Oops"]
    assert titles(alice, "completed") == []


def test_ticking_twice_keeps_the_first_time(alice: TestClient, clock: FakeClock) -> None:
    todo = add(alice, "Twice")
    alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": True})
    clock.now = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)

    again = alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": True}).json()

    assert again["completedAt"] == "2026-11-22T06:00:00.000Z"


# ---- US-12: edit and delete -------------------------------------------------------


def test_edit_changes_only_the_fields_sent(alice: TestClient, clock: FakeClock) -> None:
    todo = add(alice, "Old", notes="keep me", priority="low")
    clock.now = datetime(2026, 11, 22, 8, 0, tzinfo=UTC)

    edited = alice.patch(f"{TODOS}/{todo['todoId']}", json={"title": "New"}).json()

    assert edited["title"] == "New"
    assert edited["notes"] == "keep me"
    assert edited["priority"] == "low"
    assert edited["updatedAt"] == "2026-11-22T08:00:00.000Z"
    assert edited["createdAt"] == "2026-11-22T06:00:00.000Z"


def test_null_clears_an_optional_field(alice: TestClient) -> None:
    todo = add(alice, "Dated", dueDate="2026-11-30", priority="high", notes="x")

    edited = alice.patch(
        f"{TODOS}/{todo['todoId']}", json={"dueDate": None, "priority": None, "notes": None}
    ).json()

    assert (edited["dueDate"], edited["priority"], edited["notes"]) == (None, None, None)
    assert titles(alice, "upcoming") == []
    assert titles(alice, "all") == ["Dated"]


def test_changing_the_due_date_moves_it_between_views(alice: TestClient) -> None:
    todo = add(alice, "Move me", dueDate="2026-11-30")
    assert titles(alice, "upcoming") == ["Move me"]

    alice.patch(f"{TODOS}/{todo['todoId']}", json={"dueDate": "2026-11-20"})

    assert titles(alice, "upcoming") == []
    assert titles(alice, "today") == ["Move me"]


def test_delete_removes_the_todo_for_good(alice: TestClient, todos_db: "Table") -> None:
    todo = add(alice, "Bye")

    response = alice.delete(f"{TODOS}/{todo['todoId']}")

    assert response.status_code == 204
    assert alice.get(f"{TODOS}/{todo['todoId']}").status_code == 404
    assert todos_db.scan()["Count"] == 0
    assert alice.delete(f"{TODOS}/{todo['todoId']}").status_code == 404


def test_patch_to_an_unknown_id_creates_nothing(alice: TestClient, todos_db: "Table") -> None:
    response = alice.patch(f"{TODOS}/01JD0000000000000000000000", json={"title": "Ghost"})

    assert response.status_code == 404
    assert todos_db.scan()["Count"] == 0


def test_a_write_from_another_tab_in_between_is_a_conflict(
    alice: TestClient, todos_db: "Table"
) -> None:
    todo = add(alice, "Two tabs")
    key = {"PK": "USER#alice", "SK": f"TODO#{todo['todoId']}"}
    stored = todos_db.get_item(Key=key)["Item"]

    # The other tab's write lands between this request's read and its write. To make
    # that happen on cue, the first read returns the old copy and writes the other
    # tab's change behind it.
    original_get = todos_db.get_item
    calls = {"n": 0}

    def stale_get(**kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            todos_db.put_item(Item={**stored, "version": 2, "title": "Other tab"})
            return {"Item": stored}
        return original_get(**kwargs)

    todos_db.get_item = stale_get  # type: ignore[method-assign]
    try:
        response = alice.patch(f"{TODOS}/{todo['todoId']}", json={"title": "This tab"})
    finally:
        todos_db.get_item = original_get  # type: ignore[method-assign]

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert todos_db.get_item(Key=key)["Item"]["title"] == "Other tab"


def test_a_todo_written_before_versions_can_still_be_edited(
    alice: TestClient, todos_db: "Table"
) -> None:
    todo = add(alice, "Old item")
    key = {"PK": "USER#alice", "SK": f"TODO#{todo['todoId']}"}
    item = todos_db.get_item(Key=key)["Item"]
    del item["version"]
    todos_db.put_item(Item=item)

    response = alice.patch(f"{TODOS}/{todo['todoId']}", json={"title": "Edited"})

    assert response.status_code == 200
    assert todos_db.get_item(Key=key)["Item"]["version"] == 1


# ---- US-13: views -----------------------------------------------------------------


def test_the_four_views(alice: TestClient, clock: FakeClock) -> None:
    # 06:00 UTC is 11:30 in Kolkata (alice): today is 2026-11-22.
    add(alice, "overdue", dueDate="2026-11-20")
    add(alice, "today", dueDate="2026-11-22")
    add(alice, "tomorrow", dueDate="2026-11-23")
    add(alice, "next month", dueDate="2026-12-15")
    add(alice, "someday")
    done = add(alice, "done", dueDate="2026-11-21")
    alice.patch(f"{TODOS}/{done['todoId']}", json={"completed": True})

    assert titles(alice, "today") == ["overdue", "today"]
    assert titles(alice, "upcoming") == ["tomorrow", "next month"]
    assert titles(alice, "all") == ["overdue", "today", "tomorrow", "next month", "someday"]
    assert titles(alice, "completed") == ["done"]
    assert alice.get(TODOS, params={"view": "today"}).json()["today"] == "2026-11-22"


def test_all_is_the_default_view(alice: TestClient) -> None:
    add(alice, "one")

    assert [item["title"] for item in alice.get(TODOS).json()["items"]] == ["one"]


def test_completed_is_newest_first(alice: TestClient, clock: FakeClock) -> None:
    for hour, title in ((7, "first done"), (8, "second done")):
        todo = add(alice, title)
        clock.now = datetime(2026, 11, 22, hour, 0, tzinfo=UTC)
        alice.patch(f"{TODOS}/{todo['todoId']}", json={"completed": True})

    assert titles(alice, "completed") == ["second done", "first done"]


def test_today_uses_each_users_time_zone(
    alice: TestClient, bob: TestClient, clock: FakeClock
) -> None:
    # 20:00 UTC on the 22nd: already 01:30 on the 23rd in Kolkata (alice), still the
    # 22nd in London (bob).
    clock.now = datetime(2026, 11, 22, 20, 0, tzinfo=UTC)
    add(alice, "alice's", dueDate="2026-11-23")
    add(bob, "bob's", dueDate="2026-11-23")

    assert titles(alice, "today") == ["alice's"]
    assert titles(bob, "today") == []
    assert titles(bob, "upcoming") == ["bob's"]


def test_the_time_zone_database_is_in_the_image() -> None:
    from zoneinfo import ZoneInfo

    assert ZoneInfo("Asia/Kolkata").utcoffset(datetime(2026, 1, 1)) is not None


# ---- SR-32: pagination ------------------------------------------------------------


def test_lists_come_in_pages_of_50(alice: TestClient, todos_db: "Table") -> None:
    # Written straight to the table: 51 API calls would be slow and test nothing more.
    with todos_db.batch_writer() as batch:
        for n in range(51):
            todo_id = f"01JD{n:022d}"
            batch.put_item(
                Item={
                    "PK": "USER#alice",
                    "SK": f"TODO#{todo_id}",
                    "todoId": todo_id,
                    "title": f"todo {n:02d}",
                    "completed": False,
                    "createdAt": "2026-11-22T06:00:00.000Z",
                    "updatedAt": "2026-11-22T06:00:00.000Z",
                    "version": 1,
                    "GSI1PK": "USER#alice#TODO#OPEN",
                    "GSI1SK": f"NODUE#{todo_id}",
                }
            )

    first = alice.get(TODOS, params={"view": "all"}).json()
    assert len(first["items"]) == 50
    assert first["nextCursor"]
    # The cursor holds no partition key (T-043).
    padded = first["nextCursor"] + "=" * (-len(first["nextCursor"]) % 4)
    assert "USER#" not in base64.urlsafe_b64decode(padded).decode()

    second = alice.get(TODOS, params={"view": "all", "cursor": first["nextCursor"]}).json()
    assert [item["title"] for item in second["items"]] == ["todo 50"]
    assert second["nextCursor"] is None
