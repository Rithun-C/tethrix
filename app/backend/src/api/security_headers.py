"""Security headers on every response (SR-60, SR-61; ADR-0007).

With CloudFront these came from a CloudFront response headers policy. On API Gateway
there is no such feature, so the app adds them itself, to pages, files and API answers
alike. The values are the same as in the CloudFront design.
"""

from collections.abc import Sequence

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Scripts, styles and API calls only from our own address. No inline scripts, no eval,
# no framing. The sign-in server (Cognito's hosted address) is added to connect-src,
# because the browser swaps the sign-in code for tokens and revokes them there (B4).


def build_csp(extra_connect_src: Sequence[str] = ()) -> str:
    connect = " ".join(["'self'", *extra_connect_src])
    return "; ".join(
        [
            "default-src 'none'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            f"connect-src {connect}",
            "manifest-src 'self'",
            "base-uri 'none'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def build_security_headers(extra_connect_src: Sequence[str] = ()) -> dict[str, str]:
    return {
        "content-security-policy": build_csp(extra_connect_src),
        # Browsers remember for a year to use HTTPS only, for this name and names under
        # it. Browsers ignore it on plain http://localhost, so local development is
        # unaffected.
        "strict-transport-security": "max-age=31536000; includeSubDomains",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
    }


# The headers without any sign-in server, as used locally and in most tests.
SECURITY_HEADERS: dict[str, str] = build_security_headers()


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, extra_connect_src: Sequence[str] = ()) -> None:
        self.app = app
        headers = build_security_headers(extra_connect_src)
        self._encoded = [(name.encode(), value.encode()) for name, value in headers.items()]
        self._names = {name for name, _ in self._encoded}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def add_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Our values replace any the route set, so no route can weaken them.
                headers = [
                    (n, v) for n, v in message.get("headers", []) if n.lower() not in self._names
                ]
                message = {**message, "headers": headers + self._encoded}
            await send(message)

        await self.app(scope, receive, add_headers)
