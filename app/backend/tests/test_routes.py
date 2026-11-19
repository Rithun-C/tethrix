"""SR-01: every route except health needs a sign-in.

There is no sign-in yet (B4), so for now the only allowed route is health. This test
fails when a route is added, which forces the question "is it protected?" each time.
From B4 the test changes to: call every route without a token and expect 401.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

OPEN_ROUTES = {
    ("GET", "/api/v1/health"),
    # Temporary in B3, removed in B5. Answers only a byte count (routes/echo.py).
    ("POST", "/api/v1/echo"),
}


def test_only_the_expected_routes_exist(app: FastAPI) -> None:
    found = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, Route)
        for method in (route.methods or set())
        if method != "HEAD"
    }

    assert found == OPEN_ROUTES


def test_docs_pages_are_off(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
