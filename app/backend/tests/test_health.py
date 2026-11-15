from fastapi.testclient import TestClient


def test_health_is_ok_without_sign_in(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_every_response_has_a_request_id(client: TestClient) -> None:
    first = client.get("/api/v1/health").headers["x-request-id"]
    second = client.get("/api/v1/health").headers["x-request-id"]

    assert first
    assert first != second


def test_a_request_id_from_the_caller_is_ignored(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"x-request-id": "chosen-by-caller"})

    assert response.headers["x-request-id"] != "chosen-by-caller"
