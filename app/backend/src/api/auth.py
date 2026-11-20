"""Sign-in checks for every API request (B4-02, ADR-0003, SR-01 to SR-03, SR-20, SR-44).

How a request is checked:

1. The whole app has one dependency, `auth_gate`. It runs before every route.
2. Paths outside /api, and the few open API routes in OPEN_API_ROUTES, pass through.
   Every other API route needs a valid token: protected by default, so a new route
   cannot be forgotten.
3. The token must be `Authorization: Bearer <jwt>`, signed with RS256 by our issuer
   (Cognito in AWS, the local OIDC server on the laptop), not expired, an access token
   (`token_use`), for our app client (`client_id`).
4. The user's profile item must exist. After an account is deleted, its old tokens stay
   correctly signed until they expire; this check refuses them (SR-03, T-027).
5. The route gets a CurrentUser. Its user_id is the token's `sub` and nothing else
   (SR-20): no route reads a user ID from the path, query or body.

Every refusal is the same 401. The reason goes to the log, the token never does (SR-44).
"""

import json
import logging
import re
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import jwt
from fastapi import Depends, Request
from starlette.exceptions import HTTPException

log = logging.getLogger(__name__)

# The only API routes that work without a sign-in (I-03, SR-01).
OPEN_API_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/health"),
        # The public sign-in settings the frontend needs before it can sign in.
        ("GET", "/api/v1/auth/config"),
    }
)

ALGORITHM = "RS256"
# Allowed clock difference between Cognito and Lambda when checking expiry.
LEEWAY_SECONDS = 30
# At most one key refetch per this many seconds, however many unknown `kid`s arrive,
# so junk tokens cannot make us flood the issuer (T-042).
JWKS_REFETCH_SECONDS = 300
_JWKS_TIMEOUT_SECONDS = 3

# Cognito's `sub` is a UUID; the local server uses the typed name. Anything else is
# refused, so a user ID can never carry characters that change a database key (SR-20).
_SUB_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")


class AuthError(Exception):
    """A token was refused. The message is the reason, for the log only."""


@dataclass(frozen=True)
class CurrentUser:
    """The signed-in user, as proven by the token and the profile check."""

    user_id: str
    profile: Mapping[str, Any] = field(repr=False)


# ---- Keys ------------------------------------------------------------------------


class KeySource(Protocol):
    def get(self, kid: str) -> jwt.PyJWK | None: ...


def _fetch_json(url: str) -> dict[str, Any]:
    # Only ever called with the address built from our own settings (https:// to
    # Cognito in AWS, the Compose service on the laptop), never with input from a request.
    with urllib.request.urlopen(url, timeout=_JWKS_TIMEOUT_SECONDS) as response:  # noqa: S310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        data: dict[str, Any] = json.load(response)
    return data


class JwksKeys:
    """The issuer's public keys, fetched once and kept in memory.

    A key ID we have not seen triggers one refetch (the issuer may have added a key),
    but not more often than JWKS_REFETCH_SECONDS.
    """

    def __init__(
        self,
        url: str,
        *,
        fetch: Callable[[str], dict[str, Any]] = _fetch_json,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url
        self._fetch = fetch
        self._clock = clock
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None

    def get(self, kid: str) -> jwt.PyJWK | None:
        if kid not in self._keys and self._may_fetch():
            self._refresh()
        return self._keys.get(kid)

    def _may_fetch(self) -> bool:
        return self._fetched_at is None or self._clock() - self._fetched_at >= JWKS_REFETCH_SECONDS

    def _refresh(self) -> None:
        self._fetched_at = self._clock()
        try:
            data = self._fetch(self._url)
            keys = jwt.PyJWKSet.from_dict(data).keys
        except (OSError, ValueError, jwt.PyJWTError) as exc:
            # Keep the keys we had. Requests signed with an unknown key are refused.
            log.warning("could not load signing keys", extra={"error": type(exc).__name__})
            return
        self._keys = {key.key_id: key for key in keys if key.key_id}


# ---- Token checks ----------------------------------------------------------------


class TokenVerifier:
    def __init__(self, *, issuer: str, client_id: str, keys: KeySource) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self._keys = keys

    def verify(self, token: str) -> str:
        """Returns the user ID (`sub`) of a valid access token, or raises AuthError."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError("malformed token") from exc

        # Checked before any key is looked up: `none`, HS256 and the rest never get
        # near the signature check (T-001).
        if header.get("alg") != ALGORITHM:
            raise AuthError("algorithm not allowed")
        kid = header.get("kid")
        if not isinstance(kid, str):
            raise AuthError("no key ID")
        key = self._keys.get(kid)
        if key is None:
            raise AuthError("unknown key ID")

        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[ALGORITHM],
                issuer=self.issuer,
                leeway=LEEWAY_SECONDS,
                options={
                    "require": ["exp", "iat", "iss", "sub", "token_use", "client_id"],
                    # Cognito access tokens carry `client_id` instead of `aud`; it is
                    # checked below.
                    "verify_aud": False,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("expired") from exc
        except jwt.PyJWTError as exc:
            raise AuthError(f"invalid: {type(exc).__name__}") from exc

        if claims["token_use"] != "access":  # noqa: S105 - a Cognito claim name, not a password
            raise AuthError("not an access token")
        if claims["client_id"] != self.client_id:
            raise AuthError("wrong client")
        sub = claims["sub"]
        if not isinstance(sub, str) or not _SUB_PATTERN.fullmatch(sub):
            raise AuthError("bad subject")
        return sub


# ---- Profiles --------------------------------------------------------------------


class ProfileStore(Protocol):
    def get(self, user_id: str) -> Mapping[str, Any] | None: ...


# ---- FastAPI dependencies --------------------------------------------------------


def get_verifier(request: Request) -> TokenVerifier | None:
    verifier: TokenVerifier | None = request.app.state.verifier
    return verifier


def get_profiles(request: Request) -> ProfileStore:
    profiles: ProfileStore = request.app.state.profiles
    return profiles


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


def _is_open(request: Request) -> bool:
    path = request.url.path
    if path != "/api" and not path.startswith("/api/"):
        return True  # the React app and its files (ADR-0007)
    route = request.scope.get("route")
    template = getattr(route, "path", path)
    method = "GET" if request.method == "HEAD" else request.method
    return (method, template) in OPEN_API_ROUTES


def auth_gate(
    request: Request,
    verifier: TokenVerifier | None = Depends(get_verifier),  # noqa: B008 - FastAPI style
    profiles: ProfileStore = Depends(get_profiles),  # noqa: B008 - FastAPI style
) -> None:
    """Runs before every route (a plain function, so FastAPI runs it in a thread: the key
    fetch and the profile read are blocking calls)."""
    if _is_open(request):
        return
    if verifier is None:
        # Sign-in is not configured (only possible outside Lambda, see config.py).
        # Fail closed: nothing protected works.
        log.warning("sign-in refused", extra={"reason": "sign-in not configured"})
        raise _unauthorized()

    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        log.info("sign-in refused", extra={"reason": "no bearer token"})
        raise _unauthorized()

    try:
        user_id = verifier.verify(token.strip())
    except AuthError as exc:
        log.info("sign-in refused", extra={"reason": str(exc)})
        raise _unauthorized() from None

    profile = profiles.get(user_id)
    if profile is None:
        log.info("sign-in refused", extra={"reason": "no profile"})
        raise _unauthorized()

    request.state.user = CurrentUser(user_id=user_id, profile=profile)


def current_user(request: Request) -> CurrentUser:
    """For routes: the signed-in user. auth_gate has already checked everything."""
    user = getattr(request.state, "user", None)
    if not isinstance(user, CurrentUser):
        raise _unauthorized()
    return user
