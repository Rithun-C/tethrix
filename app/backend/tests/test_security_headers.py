"""SR-60, SR-61: every response carries the security headers (ADR-0007)."""

import pytest
from fastapi.testclient import TestClient

from api.security_headers import SECURITY_HEADERS


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/health"),  # a normal answer
        ("GET", "/api/v1/nope"),  # an error answer
        ("POST", "/api/v1/todos"),  # refused: no sign-in
    ],
)
def test_every_response_has_the_security_headers(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path)

    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_a_body_limit_refusal_also_has_them(client: TestClient) -> None:
    response = client.post("/api/v1/todos", content=b"x" * 20_000)

    assert response.status_code == 413
    assert (
        response.headers["content-security-policy"] == SECURITY_HEADERS["content-security-policy"]
    )


def test_the_csp_allows_no_inline_script_and_no_framing() -> None:
    csp = SECURITY_HEADERS["content-security-policy"]

    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert "frame-ancestors 'none'" in csp
