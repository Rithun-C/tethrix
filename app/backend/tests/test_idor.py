"""The two-user harness (B4-04, SR-21, T-013).

Rule: every route whose path contains an ID (`{...}`) must have a two-user test listed
in ID_ROUTES. Without it, test_every_id_route_has_a_two_user_test fails, so B5 cannot
add `/todos/{todo_id}` without proving that bob gets 404 for alice's todo.

B4 proved the user comes only from the token. B5 adds the first ID routes (todos).
"""

from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

TODO = "/api/v1/todos/{todo_id}"

# (method, path template) -> name of the test function that checks it with two users.
ID_ROUTES: dict[tuple[str, str], str] = {
    ("GET", TODO): "test_bob_cannot_read_alices_todo",
    ("PATCH", TODO): "test_bob_cannot_change_alices_todo",
    ("DELETE", TODO): "test_bob_cannot_delete_alices_todo",
}


def test_every_listed_test_exists() -> None:
    assert all(name in globals() for name in ID_ROUTES.values())


def test_every_id_route_has_a_two_user_test(app: FastAPI) -> None:
    id_routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, Route) and "{" in route.path and route.path.startswith("/api/")
        for method in (route.methods or set())
        if method != "HEAD"
    }
    missing = id_routes - ID_ROUTES.keys()
    assert not missing, f"Add a two-user test to ID_ROUTES for: {sorted(missing)}"


def test_each_user_sees_only_their_own_profile(alice: TestClient, bob: TestClient) -> None:
    assert alice.get("/api/v1/me").json() == {
        "userId": "alice",
        "timeZone": "Asia/Kolkata",
        "createdAt": "2026-11-01T09:00:00Z",
    }
    assert bob.get("/api/v1/me").json()["userId"] == "bob"
    assert bob.get("/api/v1/me").json()["timeZone"] == "Europe/London"


def test_a_user_id_in_the_request_is_ignored(bob: TestClient) -> None:
    # SR-20: nothing in the request can choose the user.
    for response in (
        bob.get("/api/v1/me", params={"userId": "alice"}),
        bob.get("/api/v1/me", headers={"X-User-Id": "alice"}),
    ):
        assert response.json()["userId"] == "bob"


# ---- Todos (B5) -------------------------------------------------------------------


@pytest.fixture
def alices_todo(alice: TestClient, todos_db: "Table") -> dict[str, Any]:
    response = alice.post(
        "/api/v1/todos",
        json={"title": "Alice's secret", "notes": "private", "dueDate": "2026-11-22"},
    )
    assert response.status_code == 201
    todo: dict[str, Any] = response.json()
    return todo


def _path(todo: dict[str, Any]) -> str:
    return f"/api/v1/todos/{todo['todoId']}"


def _not_found(response: Any) -> None:
    # Exactly the answer for a todo that does not exist (SR-21): nothing tells bob
    # that the ID is real.
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


@pytest.mark.integration
def test_bob_cannot_read_alices_todo(bob: TestClient, alices_todo: dict[str, Any]) -> None:
    _not_found(bob.get(_path(alices_todo)))


@pytest.mark.integration
def test_bob_cannot_change_alices_todo(
    alice: TestClient, bob: TestClient, alices_todo: dict[str, Any]
) -> None:
    _not_found(bob.patch(_path(alices_todo), json={"title": "Bob was here"}))
    _not_found(bob.patch(_path(alices_todo), json={"completed": True}))

    assert alice.get(_path(alices_todo)).json() == alices_todo


@pytest.mark.integration
def test_bob_cannot_delete_alices_todo(
    alice: TestClient, bob: TestClient, alices_todo: dict[str, Any], todos_db: "Table"
) -> None:
    _not_found(bob.delete(_path(alices_todo)))

    assert alice.get(_path(alices_todo)).status_code == 200
    # And bob's failed attempts left nothing behind in his own partition.
    assert todos_db.scan()["Count"] == 1


@pytest.mark.integration
@pytest.mark.parametrize("view", ["today", "upcoming", "all", "completed"])
def test_bobs_lists_never_show_alices_todos(
    bob: TestClient, alices_todo: dict[str, Any], view: str
) -> None:
    response = bob.get("/api/v1/todos", params={"view": view})

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.integration
def test_alices_cursor_gives_bob_nothing_of_alices(
    alice: TestClient, bob: TestClient, todos_db: "Table"
) -> None:
    with todos_db.batch_writer() as batch:
        for n in range(55):
            todo_id = f"01JD{n:022d}"
            batch.put_item(
                Item={
                    "PK": "USER#alice",
                    "SK": f"TODO#{todo_id}",
                    "todoId": todo_id,
                    "title": "Alice's secret",
                    "completed": False,
                    "version": 1,
                    "createdAt": "2026-11-22T06:00:00.000Z",
                    "updatedAt": "2026-11-22T06:00:00.000Z",
                    "GSI1PK": "USER#alice#TODO#OPEN",
                    "GSI1SK": f"NODUE#{todo_id}",
                }
            )
    cursor = alice.get("/api/v1/todos").json()["nextCursor"]
    assert cursor

    response = bob.get("/api/v1/todos", params={"cursor": cursor})

    # The cursor is rebuilt inside bob's own partition: it can only skip ahead in his
    # own (empty) list.
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.integration
def test_a_user_id_in_a_todo_request_is_ignored(bob: TestClient, todos_db: "Table") -> None:
    response = bob.post("/api/v1/todos?userId=alice", json={"title": "Mine"})

    assert response.status_code == 201
    items = todos_db.scan()["Items"]
    assert [item["PK"] for item in items] == ["USER#bob"]
