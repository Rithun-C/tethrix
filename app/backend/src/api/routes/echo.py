"""Temporary test endpoint for bolt B3. Removed in B5, when the first real POST exists.

B3 has to prove that a request with a body travels through CloudFront and OAC to Lambda
(ADR-0002: the browser must send the body's SHA-256 hash). No feature has a POST yet, so
this route stands in for one.

It answers only how many bytes arrived, never the content: whatever is sent cannot come
back, so it cannot be used to reflect a script into a page (XSS) and nothing is stored.
"""

from fastapi import FastAPI, Request


async def echo(request: Request) -> dict[str, int]:
    body = await request.body()
    return {"received_bytes": len(body)}


def add_routes(app: FastAPI, prefix: str) -> None:
    app.add_api_route(f"{prefix}/echo", echo, methods=["POST"])
