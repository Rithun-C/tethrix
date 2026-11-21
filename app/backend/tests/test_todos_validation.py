"""SR-30: every todo body is checked, and unknown fields are refused (T-007).

A bad body is refused before the database is touched, so most of these need no
DynamoDB. The cursor checks (T-043) are unit tests of api/todos.py.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.todos import BadCursor, _range, decode_cursor, encode_cursor

TODOS = "/api/v1/todos"
SOME_ID = "01JD0000000000000000000000"


def refused(response: Any, field: str | None = None) -> None:
    assert response.status_code == 400, response.text
    body = response.json()["error"]
    assert body["code"] in ("validation_error", "bad_request")
    if field:
        assert field in body["message"]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "title"),
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"title": "two\nlines"}, "title"),
        ({"title": "tab\there"}, "title"),
        ({"title": 5}, "title"),
        ({"title": None}, "title"),
        ({"title": "ok", "notes": "x" * 2001}, "notes"),
        ({"title": "ok", "notes": "bell\x07"}, "notes"),
        ({"title": "ok", "dueDate": "2026-02-30"}, "dueDate"),
        ({"title": "ok", "dueDate": "22-11-2026"}, "dueDate"),
        ({"title": "ok", "dueDate": "2026-11-22T00:00:00"}, "dueDate"),
        ({"title": "ok", "dueDate": "1999-12-31"}, "dueDate"),
        ({"title": "ok", "dueDate": "2101-01-01"}, "dueDate"),
        ({"title": "ok", "dueDate": 20261122}, "dueDate"),
        ({"title": "ok", "priority": "urgent"}, "priority"),
        ({"title": "ok", "priority": "HIGH"}, "priority"),
        # Unknown fields: nobody can choose the user, a key or the completion time.
        ({"title": "ok", "userId": "bob"}, "userId"),
        ({"title": "ok", "PK": "USER#bob"}, "PK"),
        ({"title": "ok", "completedAt": "2026-01-01T00:00:00Z"}, "completedAt"),
        ({"title": "ok", "completed": True}, "completed"),  # a new todo starts open
    ],
)
def test_bad_new_todos_are_refused(alice: TestClient, body: dict[str, Any], field: str) -> None:
    refused(alice.post(TODOS, json=body), field)


def test_a_body_that_is_not_json_is_refused(alice: TestClient) -> None:
    refused(alice.post(TODOS, content=b"title=hi", headers={"Content-Type": "text/plain"}))


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"title": ""}, "title"),
        ({"completed": "yes"}, "completed"),
        ({"completed": 1}, "completed"),
        ({"dueDate": "tomorrow"}, "dueDate"),
        ({"todoId": SOME_ID}, "todoId"),
        ({"version": 1}, "version"),
        ({"createdAt": "2026-01-01T00:00:00Z"}, "createdAt"),
    ],
)
def test_bad_edits_are_refused(alice: TestClient, body: dict[str, Any], field: str) -> None:
    refused(alice.patch(f"{TODOS}/{SOME_ID}", json=body), field)


@pytest.mark.parametrize("body", [{"title": None}, {"completed": None}])
def test_title_and_completed_cannot_be_cleared(alice: TestClient, body: dict[str, Any]) -> None:
    refused(alice.patch(f"{TODOS}/{SOME_ID}", json=body))


@pytest.mark.parametrize(
    "todo_id",
    ["not-a-ulid", "01jd0000000000000000000000", "01JD000000000000000000000I", "x" * 26, "1"],
)
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_an_id_that_is_not_a_ulid_is_not_found(
    alice: TestClient, method: str, todo_id: str
) -> None:
    response = alice.request(method, f"{TODOS}/{todo_id}", json={"title": "x"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("view", ["mine", "TODAY", "", "all;drop"])
def test_an_unknown_view_is_refused(alice: TestClient, view: str) -> None:
    refused(alice.get(TODOS, params={"view": view}), "view")


def test_a_long_cursor_is_refused(alice: TestClient) -> None:
    refused(alice.get(TODOS, params={"cursor": "a" * 401}), "cursor")


def test_errors_never_repeat_what_was_sent(alice: TestClient) -> None:
    response = alice.post(TODOS, json={"title": "<script>marker</script>" + "x" * 300})

    assert "marker" not in response.text


# ---- The cursor (T-043) -------------------------------------------------------------

TODAY, TOMORROW = "2026-11-22", "2026-11-23"
A_ID = "01JD0000000000000000000001"


def cursor_for(gsi_sk: str, sk: str = f"TODO#{A_ID}") -> str:
    return encode_cursor({"GSI1SK": gsi_sk, "SK": sk, "PK": "USER#alice", "GSI1PK": "anything"})


def test_the_cursor_carries_no_partition_key() -> None:
    cursor = cursor_for(f"NODUE#{A_ID}")
    rng = _range("bob", "all", TODAY, TOMORROW)

    start = decode_cursor(cursor, "bob", rng)

    # Whoever made it, the partition is the caller's own.
    assert start == {
        "PK": "USER#bob",
        "SK": f"TODO#{A_ID}",
        "GSI1PK": "USER#bob#TODO#OPEN",
        "GSI1SK": f"NODUE#{A_ID}",
    }


@pytest.mark.parametrize(
    ("cursor", "view"),
    [
        ("not base64 !!", "all"),
        ("e30", "all"),  # {}
        (cursor_for(f"NODUE#{A_ID}", sk="PROFILE"), "all"),
        (cursor_for(f"NODUE#{A_ID}", sk="TODO#short"), "all"),
        (cursor_for("NODUE#01JD0000000000000000000002"), "all"),  # sort keys disagree
        (cursor_for(f"DONE#2026-11-22T06:00:00.000Z#{A_ID}"), "all"),  # from Completed
        (cursor_for(f"NODUE#{A_ID}"), "completed"),  # from All
        (cursor_for(f"DUE#2026-11-30#{A_ID}"), "today"),  # outside Today's range
        (cursor_for(f"DUE#2026-11-20#{A_ID}"), "upcoming"),  # outside Upcoming's range
        (cursor_for(f"HABIT#x#{A_ID}"), "all"),
    ],
)
def test_a_cursor_that_does_not_fit_the_view_is_refused(cursor: str, view: str) -> None:
    rng = _range("alice", view, TODAY, TOMORROW)  # type: ignore[arg-type]

    with pytest.raises(BadCursor):
        decode_cursor(cursor, "alice", rng)
