"""GET /api/v1/auth/config: the public sign-in settings for the frontend (B4 decision 4).

The frontend reads these at start instead of having them built in, so the same image
works on the laptop (local OIDC server) and in AWS (Cognito), and B6 can promote one
image. Nothing here is secret: the browser sees all of it during sign-in anyway.

The endpoints are listed explicitly, so the browser never has to fetch the issuer's
discovery document (one fewer address in the CSP).
"""

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException

from api.config import Settings

SCOPE = "openid email"


def build_auth_config(settings: Settings) -> dict[str, str] | None:
    issuer, client_id = settings.issuer_url, settings.app_client_id
    if not issuer or not client_id:
        return None
    if settings.auth_mode == "local":
        return {
            "authority": issuer,
            "clientId": client_id,
            "scope": SCOPE,
            "authorizationEndpoint": f"{issuer}/authorize",
            "tokenEndpoint": f"{issuer}/token",
            "revocationEndpoint": f"{issuer}/revoke",
            "logoutEndpoint": f"{issuer}/endsession",
        }
    domain = settings.cognito_domain
    if not domain:
        return None
    return {
        "authority": issuer,
        "clientId": client_id,
        "scope": SCOPE,
        "authorizationEndpoint": f"{domain}/oauth2/authorize",
        "tokenEndpoint": f"{domain}/oauth2/token",
        "revocationEndpoint": f"{domain}/oauth2/revoke",
        "logoutEndpoint": f"{domain}/logout",
    }


def auth_config(request: Request) -> dict[str, str]:
    config: dict[str, str] | None = request.app.state.auth_config
    if config is None:
        raise HTTPException(status_code=503)
    return config


def add_routes(app: FastAPI, prefix: str) -> None:
    app.add_api_route(f"{prefix}/auth/config", auth_config, methods=["GET"])
