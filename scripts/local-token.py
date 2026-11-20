#!/usr/bin/env python3
"""Prints a local access token for a seed user (B4-05). Laptop only.

Signs in at the local OIDC server in Compose (http://localhost:8090) exactly as the
browser will: authorization code flow with PKCE. Useful until the frontend sign-in
exists, and for trying the API by hand:

    TOKEN=$(scripts/local-token.py alice)
    curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/me

Refuses to talk to anything but localhost. Uses only the Python standard library.
"""

import base64
import hashlib
import http.client
import json
import secrets
import sys
import urllib.parse

HOST, PORT = "localhost", 8090
CLIENT_ID = "local-app"
REDIRECT_URI = "http://localhost:5173/auth/callback"


def main() -> None:
    user = sys.argv[1] if len(sys.argv) > 1 else "alice"
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    query = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "state": secrets.token_urlsafe(8),
            "scope": "openid email",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    conn = http.client.HTTPConnection(HOST, PORT, timeout=5)

    # Step 1: "type the user name" on the sign-in page; the server redirects with a code.
    conn.request("POST", f"/local/authorize?{query}", body=urllib.parse.urlencode({"username": user}), headers=form)
    response = conn.getresponse()
    response.read()
    location = response.getheader("Location") or ""
    code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query).get("code", [""])[0]
    if not code:
        sys.exit(f"No code from the local OIDC server (status {response.status}). Is `make up` running?")

    # Step 2: swap the code and the PKCE verifier for tokens.
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        }
    )
    conn.request("POST", "/local/token", body=body, headers=form)
    tokens = json.loads(conn.getresponse().read())
    print(tokens["access_token"])


if __name__ == "__main__":
    main()
