# Test file for .semgrep/rules/no-user-id-from-request.yaml. Not part of the app.
# "ruleid:" marks a line the rule must flag. "ok:" marks a line it must leave alone.

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()


def current_user():
    return "sub-from-token"


# ruleid: no-user-id-in-route-path
@router.get("/users/{user_id}/todos")
# ruleid: no-user-id-route-parameter
def list_todos_bad_path(user_id: str):
    return []


@router.get("/todos")
# ruleid: no-user-id-route-parameter
async def list_todos_bad_query(owner_id: str = Query(...)):
    return []


@router.delete("/todos/{todo_id}")
# ruleid: no-user-id-route-parameter
def delete_todo_bad(todo_id: str, sub: str):
    return None


@router.post("/habits")
# ruleid: no-user-id-route-parameter
async def create_habit_bad(name: str, user_id=None):
    return None


class TodoCreateBad(BaseModel):
    title: str
    # ruleid: no-user-id-in-request-model
    user_id: str


class TodoUpdateBad(BaseModel):
    title: str
    # ruleid: no-user-id-in-request-model
    owner_id: str | None = None


# ok: no-user-id-in-route-path
@router.get("/todos/{todo_id}")
# ok: no-user-id-route-parameter
async def get_todo_good(todo_id: str, user: str = Depends(current_user)):
    return {"id": todo_id, "owner": user}


# ok: no-user-id-route-parameter
def build_key(user_id: str, todo_id: str) -> str:
    # Not a route: inside the app, passing the user ID from the token around is fine.
    return f"USER#{user_id}#TODO#{todo_id}"


class TodoCreateGood(BaseModel):
    # ok: no-user-id-in-request-model
    title: str


class ProfileResponse(BaseModel):
    # ok: no-user-id-in-request-model
    user_id: str
    email: str
