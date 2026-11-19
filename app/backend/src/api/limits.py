"""Request body size limit (SR-31).

Bodies larger than the limit are refused with 413 before any route runs, so a route
never has to think about huge input. The limit is 16 KB for now; pages and journal
entries get 128 KB in B8.

How it works: the body is read here, up to one byte more than the limit, and then
handed to the app as if it came straight from the network. Reading it whole is fine,
because the largest body we ever accept is small (128 KB), and on Lambda the whole
request has already arrived before our code runs anyway.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.errors import error_response

DEFAULT_MAX_BODY_BYTES = 16 * 1024

_TOO_LARGE = ("too_large", "The request is too large.")
_BAD_LENGTH = ("bad_request", "The request is not valid.")


def _declared_length(scope: Scope) -> int | None:
    """The Content-Length header as a number; None if absent; -1 if not a valid number."""
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            text = value.decode("latin-1")
            return int(text) if text.isdigit() else -1
    return None


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _declared_length(scope)
        if declared == -1:
            await error_response(400, *_BAD_LENGTH)(scope, receive, send)
            return
        # A declared size over the limit is refused without reading anything.
        if declared is not None and declared > self.max_bytes:
            await error_response(413, *_TOO_LARGE)(scope, receive, send)
            return

        # The header can be missing (chunked upload) or wrong, so count what arrives.
        chunks: list[bytes] = []
        received = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.max_bytes:
                await error_response(413, *_TOO_LARGE)(scope, receive, send)
                return
            chunks.append(chunk)
            more = message.get("more_body", False)

        body = b"".join(chunks)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            # After the body, the app may wait for the client to disconnect.
            return await receive()

        await self.app(scope, replay, send)
