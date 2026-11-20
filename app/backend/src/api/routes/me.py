"""GET /api/v1/me: the signed-in user's profile (AP1, US-03; B4-04).

The first route that reads user data. The user comes only from the checked token
(SR-20), so there is no way to ask for someone else's profile.
"""

from typing import Any

from fastapi import Depends, FastAPI

from api.auth import CurrentUser, current_user


def me(user: CurrentUser = Depends(current_user)) -> dict[str, Any]:  # noqa: B008 - FastAPI style
    # auth_gate already read the profile to prove the account exists; reuse it.
    return {
        "userId": user.user_id,
        "timeZone": user.profile.get("timeZone"),
        "createdAt": user.profile.get("createdAt"),
    }


def add_routes(app: FastAPI, prefix: str) -> None:
    app.add_api_route(f"{prefix}/me", me, methods=["GET"])
