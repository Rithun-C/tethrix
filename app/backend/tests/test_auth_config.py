"""GET /api/v1/auth/config and the CSP allowance for the sign-in server (B4 decision 4)."""

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from tests.auth_helpers import install_test_auth

COGNITO_DOMAIN = "https://tethrix-app.auth.us-east-1.amazoncognito.com"


def _cognito_app() -> TestClient:
    settings = Settings(
        log_level="INFO",
        auth_mode="cognito",
        cognito_user_pool_id="us-east-1_AbCdEf123",
        cognito_client_id="abc123def456",
        cognito_domain=COGNITO_DOMAIN,
    )
    app = create_app(settings)
    install_test_auth(app)
    return TestClient(app)


def test_cognito_config() -> None:
    response = _cognito_app().get("/api/v1/auth/config")

    assert response.status_code == 200
    assert response.json() == {
        "authority": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123",
        "clientId": "abc123def456",
        "scope": "openid email",
        "authorizationEndpoint": f"{COGNITO_DOMAIN}/oauth2/authorize",
        "tokenEndpoint": f"{COGNITO_DOMAIN}/oauth2/token",
        "revocationEndpoint": f"{COGNITO_DOMAIN}/oauth2/revoke",
        "logoutEndpoint": f"{COGNITO_DOMAIN}/logout",
    }


def test_the_csp_allows_only_our_sign_in_server_for_api_calls() -> None:
    csp = _cognito_app().get("/api/v1/health").headers["content-security-policy"]

    assert f"connect-src 'self' {COGNITO_DOMAIN};" in csp


def test_local_config() -> None:
    settings = Settings(
        log_level="INFO",
        auth_mode="local",
        local_oidc_issuer="http://localhost:8090/local",
        local_oidc_jwks_url="http://oidc:8080/local/jwks",
        local_oidc_client_id="local-app",
    )
    body = TestClient(create_app(settings)).get("/api/v1/auth/config").json()

    assert body["authority"] == "http://localhost:8090/local"
    assert body["clientId"] == "local-app"
    assert body["tokenEndpoint"] == "http://localhost:8090/local/token"


def test_not_configured_is_a_server_error_not_a_crash() -> None:
    settings = Settings(log_level="INFO", auth_mode="cognito", cognito_user_pool_id=None)
    response = TestClient(create_app(settings)).get("/api/v1/auth/config")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "internal_error"


def test_config_needs_no_sign_in(client: TestClient) -> None:
    # Open on purpose: the frontend needs it before anyone can sign in.
    assert client.get("/api/v1/auth/config").status_code in (200, 503)
