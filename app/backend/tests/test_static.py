"""The React app served from the backend (ADR-0007, T-037)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.static import ASSETS_CACHE, INDEX_CACHE
from tests.auth_helpers import bearer, install_test_auth, make_token

INDEX = "<!doctype html><title>test app</title>"


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)")
    # A file next to the static folder that must never be reachable through it.
    (tmp_path.parent / "secret.txt").write_text("do not serve")
    return tmp_path


@pytest.fixture
def site(static_dir: Path) -> TestClient:
    app = create_app(Settings(log_level="INFO", static_dir=str(static_dir)))
    install_test_auth(app)
    return TestClient(app)


def test_root_serves_the_react_app_uncached(site: TestClient) -> None:
    response = site.get("/")

    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["cache-control"] == INDEX_CACHE


@pytest.mark.parametrize("path", ["/todos", "/journal/2026-11-20", "/pages/abc"])
def test_react_routes_get_index_html(site: TestClient, path: str) -> None:
    response = site.get(path)

    assert response.status_code == 200
    assert response.text == INDEX


def test_assets_are_served_with_a_long_cache(site: TestClient) -> None:
    response = site.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.text == "console.log(1)"
    assert response.headers["cache-control"] == ASSETS_CACHE


def test_a_missing_asset_is_404_not_the_react_page(site: TestClient) -> None:
    response = site.get("/assets/missing.js")

    assert response.status_code == 404
    assert INDEX not in response.text


@pytest.mark.parametrize("path", ["/api/v1/nope", "/api", "/api/v2/health"])
def test_unknown_api_paths_need_a_sign_in_first(site: TestClient, path: str) -> None:
    # Anonymous callers cannot even learn which API paths exist.
    response = site.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("path", ["/api/v1/nope", "/api", "/api/v2/health"])
def test_unknown_api_paths_stay_json_404_when_signed_in(site: TestClient, path: str) -> None:
    response = site.get(path, headers=bearer(make_token("alice")))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_api_routes_still_win(site: TestClient) -> None:
    assert site.get("/api/v1/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    [
        "/assets/%2e%2e/%2e%2e/secret.txt",
        "/assets/..%2f..%2fsecret.txt",
        "/assets/%2e%2e%2f%2e%2e%2fsecret.txt",
    ],
)
def test_paths_outside_the_static_folder_are_refused(site: TestClient, path: str) -> None:
    # T-037. The client must not tidy up the path, so these are sent percent-encoded.
    response = site.get(path)

    assert "do not serve" not in response.text
    assert response.status_code in (400, 404)


def test_pages_and_files_carry_the_security_headers(site: TestClient) -> None:
    for path in ("/", "/todos", "/assets/index-abc123.js"):
        assert "frame-ancestors 'none'" in site.get(path).headers["content-security-policy"]


def test_start_up_fails_without_index_html(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"index\.html"):
        create_app(Settings(log_level="INFO", static_dir=str(tmp_path)))
