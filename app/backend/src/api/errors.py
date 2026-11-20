"""One error format for the whole API (SR-40):

    { "error": { "code": "not_found", "message": "Not found." } }

The frontend handles every error in one place. Messages are fixed texts or built from
field names; they never repeat what the user sent and never show internal details.
"""

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

# Status code -> (code, message). The codes are part of the API (I-03).
_KNOWN: dict[int, tuple[str, str]] = {
    400: ("bad_request", "The request is not valid."),
    401: ("unauthorized", "Sign in to continue."),
    404: ("not_found", "Not found."),
    405: ("method_not_allowed", "Method not allowed."),
    409: ("conflict", "The item was changed elsewhere. Reload and try again."),
    413: ("too_large", "The request is too large."),
    429: ("too_many_requests", "Too many requests. Try again later."),
}

INTERNAL_ERROR = ("internal_error", "Something went wrong.")


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def error_response(
    status: int, code: str, message: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(status_code=status, content=error_body(code, message), headers=headers)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101 - narrows the type
    status = exc.status_code
    if status >= 500:
        return error_response(status, *INTERNAL_ERROR)
    code, message = _KNOWN.get(status, _KNOWN[400])
    # Headers the code set on purpose, such as WWW-Authenticate on a 401, are kept.
    return error_response(status, code, message, headers=exc.headers)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101 - narrows the type
    # Name the fields that failed, but never echo the values: a rejected journal entry
    # must not come back in an error or end up in a log (SR-42).
    fields = sorted({".".join(str(part) for part in err["loc"][1:]) for err in exc.errors()})
    named = [field for field in fields if field]
    message = f"Invalid input: {', '.join(named)}." if named else "Invalid input."
    return error_response(400, "validation_error", message)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    # Crashes (any other exception) are handled in middleware.py, which also logs them.
