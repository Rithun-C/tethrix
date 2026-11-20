"""SR-02, SR-03, SR-44: the token checks (B4-02, T-001, T-027, T-042).

Each negative test changes one thing about an otherwise valid token and expects the
same plain 401.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from api.auth import JWKS_REFETCH_SECONDS, JwksKeys
from tests.auth_helpers import (
    OTHER_PRIVATE_KEY,
    PRIVATE_KEY,
    TEST_KID,
    FakeProfiles,
    bearer,
    make_claims,
    make_token,
)
from tests.conftest import LogReader

ME = "/api/v1/me"
UNAUTHORIZED = {"error": {"code": "unauthorized", "message": "Sign in to continue."}}


def _b64(data: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def assert_refused(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get(ME, headers=headers)
    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_a_valid_token_is_accepted(client: TestClient) -> None:
    response = client.get(ME, headers=bearer(make_token("alice")))

    assert response.status_code == 200
    assert response.json()["userId"] == "alice"


def test_no_token(client: TestClient) -> None:
    assert_refused(client, {})


@pytest.mark.parametrize(
    "value",
    ["Basic YWxpY2U6cHc=", "Bearer", "Bearer ", "bearer-but-not-really", "Token abc"],
)
def test_wrong_header_shapes(client: TestClient, value: str) -> None:
    assert_refused(client, {"Authorization": value})


def test_the_old_custom_header_is_not_accepted(client: TestClient) -> None:
    # ADR-0003 update: only Authorization: Bearer counts now.
    assert_refused(client, {"X-Auth-Token": make_token("alice")})


def test_garbage_token(client: TestClient) -> None:
    assert_refused(client, bearer("not.a.jwt"))


def test_alg_none_is_refused(client: TestClient) -> None:
    token = f"{_b64({'alg': 'none', 'kid': TEST_KID, 'typ': 'JWT'})}.{_b64(make_claims())}."
    assert_refused(client, bearer(token))


def test_hs256_signed_with_the_public_key_is_refused(client: TestClient) -> None:
    # The classic RSA/HMAC confusion: an attacker signs with the public key as an HMAC
    # secret, hoping the server uses the same bytes to "verify".
    public_pem = PRIVATE_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    header = {"alg": "HS256", "kid": TEST_KID, "typ": "JWT"}
    signing_input = f"{_b64(header)}.{_b64(make_claims())}".encode()
    signature = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
    token = signing_input.decode() + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    assert_refused(client, bearer(token))


def test_signed_by_another_key_with_our_key_id(client: TestClient) -> None:
    assert_refused(client, bearer(make_token("alice", key=OTHER_PRIVATE_KEY)))


def test_unknown_key_id(client: TestClient) -> None:
    assert_refused(client, bearer(make_token("alice", kid="someone-elses-key")))


def test_no_key_id(client: TestClient) -> None:
    assert_refused(client, bearer(make_token("alice", kid=None)))


def test_expired(client: TestClient) -> None:
    past = int(time.time()) - 120
    assert_refused(client, bearer(make_token("alice", iat=past - 3600, exp=past)))


def test_expired_within_the_clock_leeway_is_accepted(client: TestClient) -> None:
    just_now = int(time.time()) - 5
    response = client.get(ME, headers=bearer(make_token("alice", exp=just_now)))
    assert response.status_code == 200


def test_wrong_issuer(client: TestClient) -> None:
    other = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_OTHERPOOL"
    assert_refused(client, bearer(make_token("alice", iss=other)))


def test_wrong_client(client: TestClient) -> None:
    assert_refused(client, bearer(make_token("alice", client_id="another-app")))


def test_an_id_token_is_not_an_access_token(client: TestClient) -> None:
    assert_refused(client, bearer(make_token("alice", token_use="id")))  # noqa: S106 - claim name


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "sub", "token_use", "client_id"])
def test_required_claims(client: TestClient, missing: str) -> None:
    claims = make_claims("alice")
    del claims[missing]
    token = jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": TEST_KID})
    assert_refused(client, bearer(token))


@pytest.mark.parametrize("sub", ["alice#SK", "../bob", "a" * 129, "alice bob", ""])
def test_odd_user_ids_are_refused(client: TestClient, sub: str) -> None:
    # A user ID must never be able to change the shape of a database key (SR-20).
    assert_refused(client, bearer(make_token(sub)))


def test_a_deleted_account_is_refused(app: Any, client: TestClient) -> None:
    # SR-03, T-027: the token is still validly signed, but the profile is gone.
    profiles: FakeProfiles = app.state.profiles
    del profiles.profiles["alice"]

    assert_refused(client, bearer(make_token("alice")))


def test_sign_in_not_configured_fails_closed(app: Any, client: TestClient) -> None:
    app.state.verifier = None
    assert_refused(client, bearer(make_token("alice")))


def test_tokens_never_reach_the_logs(client: TestClient, raw_logs: list[str]) -> None:
    good = make_token("alice")
    bad = make_token("alice", client_id="another-app")
    client.get(ME, headers=bearer(good))
    client.get(ME, headers=bearer(bad))

    for token in (good, bad):
        for part in token.split("."):
            assert not any(part in line for line in raw_logs)


def test_a_refusal_logs_the_reason(client: TestClient, logs: LogReader) -> None:
    client.get(ME, headers=bearer(make_token("alice", token_use="id")))  # noqa: S106 - claim name

    refusals = [line for line in logs() if line.get("message") == "sign-in refused"]
    assert [line["reason"] for line in refusals] == ["not an access token"]


def test_the_request_log_names_the_user(alice: TestClient, logs: LogReader) -> None:
    alice.get(ME)

    requests = [line for line in logs() if line.get("message") == "request"]
    assert requests[-1]["user_id"] == "alice"
    assert requests[-1]["path"] == ME


# ---- Key cache --------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _CountingFetch:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _url: str) -> dict[str, Any]:
        self.calls += 1
        return _jwks()


def _jwks() -> dict[str, Any]:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    jwk.update({"kid": TEST_KID, "alg": "RS256", "use": "sig"})
    return {"keys": [jwk]}


def test_keys_are_fetched_once_and_cached() -> None:
    fetch = _CountingFetch()
    keys = JwksKeys("https://issuer/jwks", fetch=fetch, clock=_Clock())

    assert keys.get(TEST_KID) is not None
    assert keys.get(TEST_KID) is not None
    assert fetch.calls == 1


def test_unknown_key_ids_cannot_flood_the_issuer() -> None:
    # T-042: junk key IDs trigger at most one refetch per JWKS_REFETCH_SECONDS.
    fetch = _CountingFetch()
    clock = _Clock()
    keys = JwksKeys("https://issuer/jwks", fetch=fetch, clock=clock)
    keys.get(TEST_KID)

    for i in range(50):
        assert keys.get(f"junk-{i}") is None
    assert fetch.calls == 1

    clock.now += JWKS_REFETCH_SECONDS
    keys.get("junk-again")
    assert fetch.calls == 2


def test_a_failed_fetch_keeps_the_old_keys() -> None:
    clock = _Clock()
    answers: list[Any] = [_jwks(), OSError("network down")]

    def fetch(_: str) -> dict[str, Any]:
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer  # type: ignore[no-any-return]

    keys = JwksKeys("https://issuer/jwks", fetch=fetch, clock=clock)
    assert keys.get(TEST_KID) is not None
    clock.now += JWKS_REFETCH_SECONDS
    assert keys.get("unknown") is None  # refetch fails
    assert keys.get(TEST_KID) is not None
