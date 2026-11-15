"""SR-40: one error format, and a crash shows no internal detail."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from tests.conftest import LogReader

SECRET_TEXT = "dear-diary-marker-7f3a"  # noqa: S105 - a marker to search for, not a password


def test_unknown_path_uses_the_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


def test_wrong_method_uses_the_error_format(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_crash_gives_a_plain_500_and_logs_where(app: FastAPI, logs: LogReader) -> None:
    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(f"could not save: {SECRET_TEXT}")

    response = TestClient(app).get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong."}
    }
    assert SECRET_TEXT not in response.text

    error = next(line for line in logs() if line["message"] == "unhandled error")
    assert error["error_type"] == "RuntimeError"
    assert any("in boom" in place for place in error["where"])
    # The log line and the response carry the same ID, so one leads to the other.
    assert error["request_id"] == response.headers["x-request-id"]


def test_invalid_input_names_the_field_but_not_the_value(app: FastAPI) -> None:
    class Entry(BaseModel):
        mood: int
        text: str

    @app.post("/entry")
    def entry(body: Entry) -> None:
        return None

    response = TestClient(app).post("/entry", json={"mood": SECRET_TEXT, "text": "x"})

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "validation_error", "message": "Invalid input: mood."}
    }
    assert SECRET_TEXT not in response.text
