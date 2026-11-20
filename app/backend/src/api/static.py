"""Serves the built React app from the same Lambda as the API (ADR-0007).

The frontend build (index.html plus content-hashed files in assets/) is copied into the
backend image at STATIC_DIR. Then:

- /assets/<file>   the file itself, cached by browsers for a year. The names contain a
                   hash of the content, so a new build always has new names.
- /api/...         never here: the API routes answer, and an unknown API path stays a
                   JSON 404 instead of turning into the React page.
- anything else    index.html, never cached, so React Router can show the right screen
                   for /todos or a reload on /journal/2026-11-20.

Locally, Vite serves the frontend and STATIC_DIR is unset, so none of this is added.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

ASSETS_CACHE = "public, max-age=31536000, immutable"
INDEX_CACHE = "no-cache"


class _CachedStaticFiles(StaticFiles):
    """Starlette's static files, plus the long cache header.

    StaticFiles itself refuses any path that leads outside its folder (for example
    /assets/../../etc/passwd), so it cannot be used to read other files (T-037).
    """

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["cache-control"] = ASSETS_CACHE
        return response


def add_routes(app: FastAPI, static_dir: str, api_prefix: str) -> None:
    root = Path(static_dir)
    index = root / "index.html"
    if not index.is_file():
        # Fail at start-up, not on the first visitor: a deploy without the frontend
        # build is a broken deploy.
        raise RuntimeError(f"STATIC_DIR is set but {index} does not exist")

    app.mount("/assets", _CachedStaticFiles(directory=root / "assets"), name="assets")

    api_root = api_prefix.split("/")[1]  # "api"

    async def react_app(path: str) -> FileResponse:
        if path == api_root or path.startswith(f"{api_root}/"):
            raise HTTPException(status_code=404)
        return FileResponse(index, headers={"cache-control": INDEX_CACHE})

    # Added last, so every API route is matched before this catch-all.
    app.add_api_route("/{path:path}", react_app, methods=["GET", "HEAD"], include_in_schema=False)
