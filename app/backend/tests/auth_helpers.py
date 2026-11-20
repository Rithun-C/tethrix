"""Test tokens and test users (B4-04).

The app under test trusts one RSA key that exists only in the test process. Tokens are
made with the same claims Cognito puts in an access token, then changed one at a time
in the negative tests.
"""

import time
from collections.abc import Mapping
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from api.auth import TokenVerifier

TEST_ISSUER = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL"
TEST_CLIENT_ID = "testclient123"
TEST_KID = "test-key-1"

# Made once per test run; never written anywhere.
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

PROFILES: dict[str, dict[str, Any]] = {
    "alice": {"timeZone": "Asia/Kolkata", "createdAt": "2026-11-01T09:00:00Z"},
    "bob": {"timeZone": "Europe/London", "createdAt": "2026-11-01T09:00:00Z"},
}


class StaticKeys:
    def __init__(self) -> None:
        public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
        public_jwk.update({"kid": TEST_KID, "alg": "RS256", "use": "sig"})
        self.key = jwt.PyJWK(public_jwk)

    def get(self, kid: str) -> jwt.PyJWK | None:
        return self.key if kid == TEST_KID else None


class FakeProfiles:
    def __init__(self, profiles: Mapping[str, Mapping[str, Any]]) -> None:
        self.profiles = dict(profiles)

    def get(self, user_id: str) -> Mapping[str, Any] | None:
        return self.profiles.get(user_id)


def install_test_auth(app: FastAPI) -> FakeProfiles:
    """Makes the app trust the test key and use in-memory profiles."""
    app.state.verifier = TokenVerifier(
        issuer=TEST_ISSUER, client_id=TEST_CLIENT_ID, keys=StaticKeys()
    )
    profiles = FakeProfiles(PROFILES)
    app.state.profiles = profiles
    return profiles


def make_claims(sub: str = "alice", **changes: Any) -> dict[str, Any]:
    """Claims of a valid access token; `changes` replace claims, None removes one."""
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": sub,
        "iss": TEST_ISSUER,
        "client_id": TEST_CLIENT_ID,
        "token_use": "access",
        "scope": "openid email",
        "iat": now,
        "exp": now + 3600,
        "jti": "test",
    }
    for name, value in changes.items():
        if value is None:
            claims.pop(name, None)
        else:
            claims[name] = value
    return claims


def make_token(
    sub: str = "alice",
    *,
    key: Any = PRIVATE_KEY,
    kid: str | None = TEST_KID,
    algorithm: str = "RS256",
    **changes: Any,
) -> str:
    headers = {"kid": kid} if kid is not None else {}
    return jwt.encode(make_claims(sub, **changes), key, algorithm=algorithm, headers=headers)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
