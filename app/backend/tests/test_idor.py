"""The two-user harness (B4-04, SR-21, T-013).

Rule: every route whose path contains an ID (`{...}`) must have a two-user test listed
in ID_ROUTES. Without it, test_every_id_route_has_a_two_user_test fails, so B5 cannot
add `/todos/{todo_id}` without proving that bob gets 404 for alice's todo.

B4 has no ID routes yet. What B4 does prove: the user comes only from the token.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

# (method, path template) -> name of the test function that checks it with two users.
ID_ROUTES: dict[tuple[str, str], str] = {}


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
