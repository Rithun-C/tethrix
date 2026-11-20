import pytest
from pydantic import ValidationError

from api.config import LAMBDA_MARKER, Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # Docker Compose sets these for the running app; remove them to see the defaults.
    for name in ("DYNAMODB_TABLE", "DYNAMODB_ENDPOINT_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings()

    assert settings.dynamodb_table == "productivity-app-data"
    assert settings.dynamodb_endpoint_url is None


def test_wrong_log_level_stops_start_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")

    with pytest.raises(ValidationError):
        Settings()


def test_local_endpoint_is_refused_in_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(LAMBDA_MARKER, "productivity-app-api")
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", "http://somewhere-else:8000")

    with pytest.raises(ValidationError, match="local-only"):
        Settings()


LOCAL_ONLY = (
    "DYNAMODB_ENDPOINT_URL",
    "AUTH_MODE",
    "LOCAL_OIDC_ISSUER",
    "LOCAL_OIDC_JWKS_URL",
    "LOCAL_OIDC_CLIENT_ID",
)
COGNITO = {
    "COGNITO_USER_POOL_ID": "us-east-1_AbCdEf123",
    "COGNITO_CLIENT_ID": "abc123def456",
    "COGNITO_DOMAIN": "https://tethrix-app.auth.us-east-1.amazoncognito.com",
}


@pytest.fixture
def in_lambda(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Looks like a deployed function: the Lambda marker and Terraform's settings, and
    none of the Compose settings."""
    monkeypatch.setenv(LAMBDA_MARKER, "productivity-app-api")
    for name in LOCAL_ONLY:
        monkeypatch.delenv(name, raising=False)
    for name, value in COGNITO.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_lambda_with_terraform_settings_starts(in_lambda: pytest.MonkeyPatch) -> None:
    settings = Settings()

    assert settings.dynamodb_endpoint_url is None
    assert settings.auth_mode == "cognito"
    assert settings.issuer_url == "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123"
    assert settings.jwks_url == settings.issuer_url + "/.well-known/jwks.json"
    assert settings.app_client_id == "abc123def456"


def test_local_sign_in_is_refused_in_lambda(in_lambda: pytest.MonkeyPatch) -> None:
    # SR-06, T-004.
    in_lambda.setenv("AUTH_MODE", "local")

    with pytest.raises(ValidationError, match="AUTH_MODE=local is a local-only setting"):
        Settings()


@pytest.mark.parametrize(
    "name", ["LOCAL_OIDC_ISSUER", "LOCAL_OIDC_JWKS_URL", "LOCAL_OIDC_CLIENT_ID"]
)
def test_local_issuer_settings_are_refused_in_lambda(
    in_lambda: pytest.MonkeyPatch, name: str
) -> None:
    in_lambda.setenv(name, "http://localhost:8090/local")

    with pytest.raises(ValidationError, match="LOCAL_OIDC_"):
        Settings()


@pytest.mark.parametrize("name", list(COGNITO))
def test_lambda_without_cognito_settings_does_not_start(
    in_lambda: pytest.MonkeyPatch, name: str
) -> None:
    in_lambda.delenv(name)

    with pytest.raises(ValidationError, match="required in Lambda"):
        Settings()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("COGNITO_USER_POOL_ID", "../../evil"),
        ("COGNITO_DOMAIN", "https://evil.example.com"),
        ("COGNITO_DOMAIN", "http://tethrix-app.auth.us-east-1.amazoncognito.com"),
        ("COGNITO_CLIENT_ID", "has spaces"),
    ],
)
def test_cognito_settings_must_look_like_cognito(
    in_lambda: pytest.MonkeyPatch, name: str, value: str
) -> None:
    # Guard 3 (B4-05): a wrong setting cannot point the app at another token issuer.
    in_lambda.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()


def test_local_mode_outside_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LAMBDA_MARKER, raising=False)
    settings = Settings(
        auth_mode="local",
        local_oidc_issuer="http://localhost:8090/local",
        local_oidc_jwks_url="http://oidc:8080/local/jwks",
        local_oidc_client_id="local-app",
    )

    assert settings.issuer_url == "http://localhost:8090/local"
    assert settings.jwks_url == "http://oidc:8080/local/jwks"
