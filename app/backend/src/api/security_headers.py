"""Security headers on every response (SR-60, SR-61; ADR-0007).

With CloudFront these came from a CloudFront response headers policy. On API Gateway
there is no such feature, so the app adds them itself, to pages, files and API answers
alike. The values are the same as in the CloudFront design.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Scripts, styles and API calls only from our own address. No inline scripts, no eval,
# no framing. Cognito is added to connect-src in B4.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "manifest-src 'self'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS: dict[str, str] = {
    "content-security-policy": CONTENT_SECURITY_POLICY,
    # Browsers remember for a year to use HTTPS only, for this name and names under it.
    # Browsers ignore it on plain http://localhost, so local development is unaffected.
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}

_ENCODED = [(name.encode(), value.encode()) for name, value in SECURITY_HEADERS.items()]
_NAMES = {name for name, _ in _ENCODED}


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def add_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Our values replace any the route set, so no route can weaken them.
                headers = [(n, v) for n, v in message.get("headers", []) if n.lower() not in _NAMES]
                message = {**message, "headers": headers + _ENCODED}
            await send(message)

        await self.app(scope, receive, add_headers)
