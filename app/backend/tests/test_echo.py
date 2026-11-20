"""The temporary B3 echo route answers a byte count and never the content."""

from fastapi.testclient import TestClient

ECHO = "/api/v1/echo"
MARKER = "<script>alert('echo-marker')</script>"


def test_echo_counts_bytes(alice: TestClient) -> None:
    response = alice.post(ECHO, content="café".encode())

    assert response.status_code == 200
    assert response.json() == {"received_bytes": 5}  # é is two bytes in UTF-8


def test_echo_never_returns_or_logs_the_body(alice: TestClient, raw_logs: list[str]) -> None:
    response = alice.post(ECHO, content=MARKER.encode())

    assert "echo-marker" not in response.text
    assert not any("echo-marker" in line for line in raw_logs)


def test_echo_accepts_an_empty_body(alice: TestClient) -> None:
    assert alice.post(ECHO).json() == {"received_bytes": 0}


def test_get_on_echo_is_not_allowed(alice: TestClient) -> None:
    response = alice.get(ECHO)

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
