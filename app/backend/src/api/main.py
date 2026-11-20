"""Builds the FastAPI app. uvicorn loads `app` from this module."""

import logging

from fastapi import Depends, FastAPI

from api import static
from api.auth import JwksKeys, TokenVerifier, auth_gate
from api.config import Settings, get_settings
from api.db import DynamoProfileStore, get_table
from api.errors import install_error_handlers
from api.limits import BodyLimitMiddleware
from api.logs import setup_logging
from api.middleware import RequestLogMiddleware
from api.routes import auth_config, echo, health, me
from api.security_headers import SecurityHeadersMiddleware

API_PREFIX = "/api/v1"

log = logging.getLogger(__name__)


def build_verifier(settings: Settings) -> TokenVerifier | None:
    issuer, client_id, jwks_url = settings.issuer_url, settings.app_client_id, settings.jwks_url
    if not (issuer and client_id and jwks_url):
        # Allowed only outside Lambda (config.py refuses to start there). Every protected
        # route then answers 401.
        log.warning("sign-in is not configured; protected routes will answer 401")
        return None
    return TokenVerifier(issuer=issuer, client_id=client_id, keys=JwksKeys(jwks_url))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    # The built-in docs pages are off. SR-01: every route except health needs a
    # sign-in, and these would be three more open routes. The docs page also loads
    # scripts from another site, which our CSP will not allow. `make openapi` writes
    # the same information to a file.
    app = FastAPI(
        title="productivity-app API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        # Runs before every route: protected by default (SR-01, api/auth.py).
        dependencies=[Depends(auth_gate)],
    )
    app.state.verifier = build_verifier(settings)
    app.state.profiles = DynamoProfileStore(get_table(settings))
    app.state.auth_config = auth_config.build_auth_config(settings)

    install_error_handlers(app)
    # The last middleware added runs first. The request log wraps everything, so a
    # request refused by the body limit still gets its log line, and the security
    # headers are added to every answer, errors included.
    app.add_middleware(BodyLimitMiddleware)
    sign_in_server = (
        [settings.cognito_domain]
        if settings.auth_mode == "cognito" and settings.cognito_domain
        else []
    )
    app.add_middleware(SecurityHeadersMiddleware, extra_connect_src=sign_in_server)
    app.add_middleware(RequestLogMiddleware)

    # Each routes module adds its routes straight onto the app, with the full path.
    # (FastAPI's include_router is not used: with it, the list of routes and the path
    # template seen by the log middleware are only reachable through FastAPI's private
    # internals. Plain routes keep `app.routes` a simple, complete list, which the
    # "every route needs a sign-in" test depends on.)
    health.add_routes(app, API_PREFIX)
    auth_config.add_routes(app, API_PREFIX)
    me.add_routes(app, API_PREFIX)
    echo.add_routes(app, API_PREFIX)  # temporary, removed in B5; needs a sign-in since B4

    # The React app, only where its build is in the image (AWS, kind). Must come after
    # every API route: it ends with a catch-all.
    if settings.static_dir:
        static.add_routes(app, settings.static_dir, API_PREFIX)
    return app


app = create_app()
