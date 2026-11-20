"""Request logging and crash handling.

For every request this writes exactly one log line (SR-41): request ID, method, path
template, status and duration. It never logs bodies, headers or query strings (SR-42).

If the code crashes, the caller gets a plain 500 in the standard error format, and the
log gets the error type and where it happened, tied together by the request ID.
"""

import logging
import time
import traceback
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.errors import INTERNAL_ERROR, error_response

logger = logging.getLogger("api.request")

REQUEST_ID_HEADER = "x-request-id"


def _path_template(scope: Scope) -> str:
    """The route's pattern, such as /api/v1/todos/{todo_id}, not the real path.

    The real path holds item IDs, and for unknown paths whatever a stranger typed.
    The pattern says which endpoint was called and nothing else.
    """
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def _user_id(scope: Scope) -> str | None:
    user = (scope.get("state") or {}).get("user")
    return getattr(user, "user_id", None)


def _where(exc: BaseException) -> list[str]:
    """Code locations of a crash, without the exception's message.

    The message can contain user data (for example the text that failed to save), so
    it is left out. File, line and function are enough to find the bug.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    return [f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in frames[-8:]]


class RequestLogMiddleware:
    """Plain ASGI middleware: it wraps the whole app, one call per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Always our own ID. An ID sent by the caller is ignored: it would let a
        # stranger write text of their choice into our logs.
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            status = 500
            logger.error(
                "unhandled error",
                extra={
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                    "where": _where(exc),
                },
            )
            if not response_started:
                response = error_response(500, *INTERNAL_ERROR)
                await response(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": _path_template(scope),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    # Who, for an audit trail: the user ID from a checked token (never
                    # the token itself, SR-44). Absent on open routes and refusals.
                    "user_id": _user_id(scope),
                },
            )
