"""SR-31: bodies over the limit are refused with 413, in the standard error format."""

from collections.abc import Iterator

from fastapi.testclient import TestClient

from api.limits import DEFAULT_MAX_BODY_BYTES
from tests.conftest import LogReader

ECHO = "/api/v1/echo"
TOO_LARGE = {"error": {"code": "too_large", "message": "The request is too large."}}


def test_body_at_the_limit_is_accepted(alice: TestClient) -> None:
    response = alice.post(ECHO, content=b"x" * DEFAULT_MAX_BODY_BYTES)

    assert response.status_code == 200
    assert response.json() == {"received_bytes": DEFAULT_MAX_BODY_BYTES}


def test_body_one_byte_over_the_limit_is_refused(alice: TestClient) -> None:
    response = alice.post(ECHO, content=b"x" * (DEFAULT_MAX_BODY_BYTES + 1))

    assert response.status_code == 413
    assert response.json() == TOO_LARGE


def test_body_without_a_length_header_is_counted(alice: TestClient) -> None:
    # A generator makes the client send the body in chunks, with no Content-Length.
    # The limit must still hold when the size is not announced.
    def chunks() -> Iterator[bytes]:
        for _ in range(20):
            yield b"x" * 1024

    response = alice.post(ECHO, content=chunks())

    assert response.status_code == 413
    assert response.json() == TOO_LARGE


def test_a_false_length_header_is_not_trusted(alice: TestClient) -> None:
    # The header claims a small body; the real body is larger.
    def chunks() -> Iterator[bytes]:
        yield b"x" * (DEFAULT_MAX_BODY_BYTES + 100)

    response = alice.post(ECHO, content=chunks(), headers={"Content-Length": "10"})

    assert response.status_code in (400, 413)


def test_a_broken_length_header_is_a_bad_request(alice: TestClient) -> None:
    response = alice.post(ECHO, content=b"{}", headers={"Content-Length": "abc"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_a_refused_request_is_still_logged(alice: TestClient, logs: LogReader) -> None:
    alice.post(ECHO, content=b"x" * (DEFAULT_MAX_BODY_BYTES + 1))

    lines = [line for line in logs() if line.get("message") == "request"]
    assert len(lines) == 1
    assert lines[0]["status"] == 413
    assert "request_id" in lines[0]
