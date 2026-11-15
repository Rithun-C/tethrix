"""SR-41: one structured line per request. SR-42: content never reaches the logs."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tests.conftest import LogReader

MARKER = "dear-diary-marker-7f3a"


def _request_lines(logs: LogReader) -> list[dict[str, object]]:
    return [line for line in logs() if line["message"] == "request"]


def test_one_line_per_request_with_the_expected_fields(client: TestClient, logs: LogReader) -> None:
    client.get("/api/v1/health")

    lines = _request_lines(logs)
    assert len(lines) == 1
    line = lines[0]
    assert line["method"] == "GET"
    assert line["path"] == "/api/v1/health"
    assert line["status"] == 200
    assert isinstance(line["duration_ms"], float)
    assert line["request_id"]
    assert line["time"]
    assert line["level"] == "INFO"


def test_path_is_the_template_not_the_real_path(app: FastAPI, logs: LogReader) -> None:
    @app.get("/things/{thing_id}")
    def thing(thing_id: str) -> dict[str, str]:
        return {"id": thing_id}

    TestClient(app).get("/things/abc123")

    assert _request_lines(logs)[0]["path"] == "/things/{thing_id}"


def test_unknown_paths_are_not_written_to_the_log(client: TestClient, logs: LogReader) -> None:
    client.get(f"/{MARKER}")

    line = _request_lines(logs)[0]
    assert line["path"] == "unmatched"
    assert line["status"] == 404


def test_bodies_headers_and_query_strings_never_reach_the_logs(
    app: FastAPI, raw_logs: list[str]
) -> None:
    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"length": len(await request.body())}

    @app.post("/crash")
    async def crash(request: Request) -> None:
        raise ValueError((await request.body()).decode())

    client = TestClient(app)
    for path in ("/echo", "/crash"):
        client.post(
            f"{path}?q={MARKER}",
            content=f"body {MARKER}",
            headers={"X-Auth-Token": f"token-{MARKER}"},
        )

    assert len(raw_logs) >= 3  # two request lines and one error line
    assert all(MARKER not in line for line in raw_logs)
