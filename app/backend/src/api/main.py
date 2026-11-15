"""Builds the FastAPI app. uvicorn loads `app` from this module."""

from fastapi import FastAPI

from api.config import Settings, get_settings
from api.errors import install_error_handlers
from api.logs import setup_logging
from api.middleware import RequestLogMiddleware
from api.routes import health

API_PREFIX = "/api/v1"


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
    )

    install_error_handlers(app)
    app.add_middleware(RequestLogMiddleware)

    # Each routes module adds its routes straight onto the app, with the full path.
    # (FastAPI's include_router is not used: with it, the list of routes and the path
    # template seen by the log middleware are only reachable through FastAPI's private
    # internals. Plain routes keep `app.routes` a simple, complete list, which the
    # "every route needs a sign-in" test depends on.)
    health.add_routes(app, API_PREFIX)
    return app


app = create_app()
