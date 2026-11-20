"""Health check: needs no sign-in (I-03, SR-01; listed in api/auth.py OPEN_API_ROUTES)."""

from fastapi import FastAPI


def health() -> dict[str, str]:
    # Does not call the database on purpose. If it did, a short database problem would
    # make the whole API look down, and every check would cost a database read.
    return {"status": "ok"}


def add_routes(app: FastAPI, prefix: str) -> None:
    app.add_api_route(f"{prefix}/health", health, methods=["GET"])
