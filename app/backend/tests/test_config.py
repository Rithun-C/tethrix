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


def test_lambda_without_local_settings_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(LAMBDA_MARKER, "productivity-app-api")
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)

    assert Settings().dynamodb_endpoint_url is None
