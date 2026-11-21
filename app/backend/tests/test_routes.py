"""SR-01: every API route except the open ones needs a sign-in.

Two tests work together:
- test_every_route_is_known: adding a route makes it fail until the route is listed
  here, which forces the question "should this be open?" each time.
- test_every_protected_route_refuses_anonymous_calls: calls every route without a token
  and expects 401. Protection comes from api/auth.py for every route by default, so
  this only fails if that default is broken or a route is wrongly made open.
"""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

from api.auth import OPEN_API_ROUTES

PROTECTED_ROUTES = {
    ("GET", "/api/v1/me"),
    ("GET", "/api/v1/todos"),
    ("POST", "/api/v1/todos"),
    ("GET", "/api/v1/todos/{todo_id}"),
    ("PATCH", "/api/v1/todos/{todo_id}"),
    ("DELETE", "/api/v1/todos/{todo_id}"),
}


def _routes(app: FastAPI) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, Route)
        for method in (route.methods or set())
        if method != "HEAD"
    }


def test_every_route_is_known(app: FastAPI) -> None:
    assert _routes(app) == OPEN_API_ROUTES | PROTECTED_ROUTES


def test_open_routes_are_only_health_and_sign_in_settings() -> None:
    assert {("GET", "/api/v1/health"), ("GET", "/api/v1/auth/config")} == OPEN_API_ROUTES


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "some-id", path)


@pytest.mark.parametrize(("method", "path"), sorted(PROTECTED_ROUTES))
def test_every_protected_route_refuses_anonymous_calls(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, _concrete(path))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_all_api_routes_are_covered_by_the_two_lists(app: FastAPI) -> None:
    api_routes = {route for route in _routes(app) if route[1].startswith("/api/")}
    assert api_routes <= OPEN_API_ROUTES | PROTECTED_ROUTES


def test_docs_pages_are_off(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
