"""Todos API (B5-01, US-10 to US-13, I-03).

    GET    /todos?view=today|upcoming|all|completed&cursor=   one page of a view
    GET    /todos/{todo_id}                                   one todo, with notes
    POST   /todos                                             add
    PATCH  /todos/{todo_id}                                   edit, tick, untick
    DELETE /todos/{todo_id}                                   delete for good

The user comes only from the checked token (SR-20). Every body is checked by a model
that refuses unknown fields (SR-30), so nobody can send userId, a key or completedAt.
Another user's todo answers 404, exactly like a missing one (SR-21).
"""

import logging
import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Query, Request, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, StrictBool, StringConstraints
from starlette.exceptions import HTTPException
from ulid import ULID

from api.auth import CurrentUser, current_user
from api.todos import (
    TODO_ID_PATTERN,
    BadCursor,
    DynamoTodoStore,
    TodoChanged,
    TodoNotFound,
    View,
)

log = logging.getLogger(__name__)

TITLE_MAX = 200
NOTES_MAX = 2000

# Line breaks, tabs and other control characters have no place in a one-line title.
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
# Notes may have line breaks and tabs, but no other control characters.
_NOTES_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean_title(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= TITLE_MAX:
        raise ValueError(f"must be 1 to {TITLE_MAX} characters")
    if _CONTROL.search(value):
        raise ValueError("must be one line of text")
    return value


def _clean_notes(value: str) -> str:
    if _NOTES_CONTROL.search(value):
        raise ValueError("contains control characters")
    return value


def _check_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as err:
        raise ValueError("must be a real date") from err
    # Four-digit years in a narrow range keep DUE#<date> keys in date order.
    if not 2000 <= parsed.year <= 2100:
        raise ValueError("year must be 2000 to 2100")
    return value


Title = Annotated[str, StringConstraints(max_length=1000), AfterValidator(_clean_title)]
Notes = Annotated[str, StringConstraints(max_length=NOTES_MAX), AfterValidator(_clean_notes)]
DueDate = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"), AfterValidator(_check_date)
]
Priority = Literal["low", "medium", "high"]


class TodoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    notes: Notes | None = None
    dueDate: DueDate | None = None
    priority: Priority | None = None


class TodoPatch(BaseModel):
    """Only the fields sent are changed. null clears an optional field."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    notes: Notes | None = None
    dueDate: DueDate | None = None
    priority: Priority | None = None
    completed: StrictBool | None = None

    def changes(self) -> dict[str, Any]:
        sent = {name: getattr(self, name) for name in self.model_fields_set}
        if "title" in sent and sent["title"] is None:
            raise HTTPException(status_code=400)  # a title can be changed, not removed
        if "completed" in sent and sent["completed"] is None:
            raise HTTPException(status_code=400)
        return sent


# ---- Helpers ---------------------------------------------------------------------

Clock = Callable[[], datetime]


def _store(request: Request) -> DynamoTodoStore:
    store: DynamoTodoStore = request.app.state.todos
    return store


def _now(request: Request) -> datetime:
    clock: Clock = request.app.state.clock
    return clock()


def _timestamp(moment: datetime) -> str:
    """UTC, milliseconds, `Z`: sorts as text in time order."""
    return (
        moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"
    )


def _today(user: CurrentUser, moment: datetime) -> date:
    """Today's date where the user lives (US-13), from the profile's time zone."""
    name = user.profile.get("timeZone")
    try:
        zone = ZoneInfo(str(name)) if name else UTC
    except (ZoneInfoNotFoundError, ValueError):
        log.warning("profile has an unknown time zone; using UTC")
        zone = UTC
    return moment.astimezone(zone).date()


def _todo_id(todo_id: str) -> str:
    # Checked before any key is built. Not a ULID = cannot exist = 404.
    if not TODO_ID_PATTERN.fullmatch(todo_id):
        raise HTTPException(status_code=404)
    return todo_id


# ---- Handlers --------------------------------------------------------------------

UserDep = Annotated[CurrentUser, Depends(current_user)]


def list_todos(
    request: Request,
    user: UserDep,
    view: View = "all",
    cursor: Annotated[str | None, Query(max_length=400)] = None,
) -> dict[str, Any]:
    today = _today(user, _now(request))
    try:
        items, next_cursor = _store(request).list_view(
            user.user_id,
            view,
            today=today.isoformat(),
            tomorrow=(today + timedelta(days=1)).isoformat(),
            cursor=cursor,
        )
    except BadCursor as err:
        raise HTTPException(status_code=400) from err
    return {"items": items, "nextCursor": next_cursor, "today": today.isoformat()}


def get_todo(request: Request, user: UserDep, todo_id: str) -> dict[str, Any]:
    try:
        return _store(request).get(user.user_id, _todo_id(todo_id))
    except TodoNotFound as err:
        raise HTTPException(status_code=404) from err


def create_todo(
    request: Request, response: Response, user: UserDep, body: TodoCreate
) -> dict[str, Any]:
    response.status_code = 201
    return _store(request).create(
        user.user_id,
        str(ULID()),
        body.model_dump(),
        _timestamp(_now(request)),
    )


def update_todo(request: Request, user: UserDep, todo_id: str, body: TodoPatch) -> dict[str, Any]:
    changes = body.changes()
    try:
        return _store(request).update(
            user.user_id, _todo_id(todo_id), changes, _timestamp(_now(request))
        )
    except TodoNotFound as err:
        raise HTTPException(status_code=404) from err
    except TodoChanged as err:
        raise HTTPException(status_code=409) from err


def delete_todo(request: Request, user: UserDep, todo_id: str) -> Response:
    try:
        _store(request).delete(user.user_id, _todo_id(todo_id))
    except TodoNotFound as err:
        raise HTTPException(status_code=404) from err
    return Response(status_code=204)


def add_routes(app: FastAPI, prefix: str) -> None:
    app.add_api_route(f"{prefix}/todos", list_todos, methods=["GET"])
    app.add_api_route(f"{prefix}/todos", create_todo, methods=["POST"])
    app.add_api_route(f"{prefix}/todos/{{todo_id}}", get_todo, methods=["GET"])
    app.add_api_route(f"{prefix}/todos/{{todo_id}}", update_todo, methods=["PATCH"])
    app.add_api_route(f"{prefix}/todos/{{todo_id}}", delete_todo, methods=["DELETE"])
