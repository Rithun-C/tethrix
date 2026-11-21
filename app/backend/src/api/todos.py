"""The todos repository (B5-02): the only code that reads or writes todo items.

Keys follow I-08:

    item   PK=USER#<user>  SK=TODO#<todoId>
    GSI1   open, with a due date   USER#<user>#TODO#OPEN  DUE#<dueDate>#<todoId>
           open, no due date       USER#<user>#TODO#OPEN  NODUE#<todoId>
           completed               USER#<user>#TODO#DONE  DONE#<completedAt>#<todoId>

Every key starts with the user ID given by the caller, which routes take only from the
checked token (SR-20). No function here accepts a key, or a part of one, from outside;
the list cursor carries only sort-key parts and the partition is always rebuilt
(T-043).
"""

import base64
import binascii
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from api.db import GSI1, user_pk

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

View = Literal["today", "upcoming", "all", "completed"]

PAGE_SIZE = 50  # SR-32

# A ULID: 26 characters of Crockford base32 (no I, L, O, U).
TODO_ID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

# Fields a caller may set. Everything else on the item (keys, version, timestamps) is
# set here.
EDITABLE = ("title", "notes", "dueDate", "priority")

# `~` sorts after every digit, letter and `#`, so `DUE#<date>~` is just past every key
# of that date.
_AFTER = "~"


class TodoNotFound(Exception):
    """No such todo for this user: missing, deleted, or someone else's (SR-21: all 404)."""


class TodoChanged(Exception):
    """The todo changed between our read and our write (another tab). Answer 409."""


class BadCursor(Exception):
    """A cursor we did not make, or one made for another view. Answer 400."""


def todo_sk(todo_id: str) -> str:
    return f"TODO#{todo_id}"


def _open_pk(user_id: str) -> str:
    return f"{user_pk(user_id)}#TODO#OPEN"


def _done_pk(user_id: str) -> str:
    return f"{user_pk(user_id)}#TODO#DONE"


def index_keys(user_id: str, item: Mapping[str, Any]) -> dict[str, str]:
    """GSI1 keys for an item: they decide which list the todo shows in. Ticking a todo
    changes them, which moves it from OPEN to DONE in the index by itself."""
    todo_id = item["todoId"]
    if item.get("completed"):
        return {
            "GSI1PK": _done_pk(user_id),
            "GSI1SK": f"DONE#{item['completedAt']}#{todo_id}",
        }
    due = item.get("dueDate")
    return {
        "GSI1PK": _open_pk(user_id),
        "GSI1SK": f"DUE#{due}#{todo_id}" if due else f"NODUE#{todo_id}",
    }


@dataclass(frozen=True)
class _Range:
    pk: str
    low: str | None  # inclusive bounds of GSI1SK; None = no bound
    high: str | None
    newest_first: bool = False


def _range(user_id: str, view: View, today: str, tomorrow: str) -> _Range:
    if view == "today":
        # Overdue and due today. NODUE# sorts after DUE#, so undated todos stay out.
        return _Range(_open_pk(user_id), "DUE#", f"DUE#{today}{_AFTER}")
    if view == "upcoming":
        return _Range(_open_pk(user_id), f"DUE#{tomorrow}", f"DUE#9999{_AFTER}")
    if view == "all":
        return _Range(_open_pk(user_id), None, None)
    return _Range(_done_pk(user_id), None, None, newest_first=True)


# ---- Cursor ----------------------------------------------------------------------


def encode_cursor(last_key: Mapping[str, Any]) -> str:
    """Only the sort-key parts go to the browser, never the partition key."""
    raw = json.dumps({"g": last_key["GSI1SK"], "s": last_key["SK"]}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, user_id: str, rng: _Range) -> dict[str, str]:
    """Rebuild DynamoDB's start key with the caller's own partition. A cursor that does
    not fit the view's range is refused, so it cannot widen a query."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (binascii.Error, ValueError, UnicodeDecodeError) as err:
        raise BadCursor from err
    if not isinstance(data, dict) or set(data) != {"g", "s"}:
        raise BadCursor
    gsi_sk, sk = data["g"], data["s"]
    if not isinstance(gsi_sk, str) or not isinstance(sk, str):
        raise BadCursor
    todo_id = sk.removeprefix("TODO#")
    if sk == todo_id or not TODO_ID_PATTERN.fullmatch(todo_id):
        raise BadCursor
    if not gsi_sk.endswith(f"#{todo_id}") or len(gsi_sk) > 100:
        raise BadCursor
    is_done = rng.pk.endswith("#DONE")
    allowed = ("DONE#",) if is_done else ("DUE#", "NODUE#")
    if not gsi_sk.startswith(allowed):
        raise BadCursor
    if (rng.low is not None and gsi_sk < rng.low) or (rng.high is not None and gsi_sk > rng.high):
        raise BadCursor
    return {"PK": user_pk(user_id), "SK": sk, "GSI1PK": rng.pk, "GSI1SK": gsi_sk}


# ---- The repository ----------------------------------------------------------------


def _summary(item: Mapping[str, Any]) -> dict[str, Any]:
    """What a list shows. The index copies only title, dueDate, priority and completed
    (I-08); the todo ID comes from SK and completedAt from the DONE sort key."""
    todo_id = str(item["SK"]).removeprefix("TODO#")
    gsi_sk = str(item["GSI1SK"])
    completed = bool(item.get("completed"))
    completed_at = gsi_sk.split("#")[1] if completed and gsi_sk.startswith("DONE#") else None
    return {
        "todoId": todo_id,
        "title": item.get("title"),
        "dueDate": item.get("dueDate"),
        "priority": item.get("priority"),
        "completed": completed,
        "completedAt": completed_at,
    }


def _detail(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "todoId": item["todoId"],
        "title": item["title"],
        "notes": item.get("notes"),
        "dueDate": item.get("dueDate"),
        "priority": item.get("priority"),
        "completed": bool(item.get("completed")),
        "completedAt": item.get("completedAt"),
        "createdAt": item["createdAt"],
        "updatedAt": item["updatedAt"],
    }


def _is_condition_failure(err: ClientError) -> bool:
    return err.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def _same_version(old: Mapping[str, Any]) -> Any:
    """Write only if nobody wrote since our read. An item without a version (written
    before B5) must still have none."""
    if "version" in old:
        return Attr("version").eq(old["version"])
    return Attr("version").not_exists()


def _without_empty(item: dict[str, Any]) -> dict[str, Any]:
    # Optional fields that are cleared are left off the item, not stored as null.
    return {key: value for key, value in item.items() if value is not None and value != ""}


class DynamoTodoStore:
    def __init__(self, table: "Table") -> None:
        self._table = table

    def create(
        self, user_id: str, todo_id: str, fields: Mapping[str, Any], now: str
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "PK": user_pk(user_id),
            "SK": todo_sk(todo_id),
            "todoId": todo_id,
            **{name: fields.get(name) for name in EDITABLE},
            "completed": False,
            "createdAt": now,
            "updatedAt": now,
            "version": 1,
        }
        item = _without_empty(item)
        item.update(index_keys(user_id, item))
        # A ULID is unique, but the condition makes sure a create can never overwrite.
        self._table.put_item(Item=item, ConditionExpression=Attr("PK").not_exists())
        return _detail(item)

    def _get_item(self, user_id: str, todo_id: str) -> dict[str, Any] | None:
        response = self._table.get_item(
            Key={"PK": user_pk(user_id), "SK": todo_sk(todo_id)}, ConsistentRead=True
        )
        item = response.get("Item")
        return dict(item) if item else None

    def get(self, user_id: str, todo_id: str) -> dict[str, Any]:
        item = self._get_item(user_id, todo_id)
        if item is None:
            raise TodoNotFound
        return _detail(item)

    def update(
        self,
        user_id: str,
        todo_id: str,
        changes: Mapping[str, Any],
        now: str,
    ) -> dict[str, Any]:
        """Apply `changes` (only the fields the caller sent; None clears one).

        Read, change, then write back only if nobody wrote in between (the version
        number, optimistic concurrency): the index keys depend on several fields, so
        the whole item is rewritten.
        """
        old = self._get_item(user_id, todo_id)
        if old is None:
            raise TodoNotFound
        new = {k: v for k, v in old.items() if k not in ("GSI1PK", "GSI1SK")}
        for name in EDITABLE:
            if name in changes:
                new[name] = changes[name]
        if "completed" in changes:
            done = bool(changes["completed"])
            if done and not old.get("completed"):
                new["completed"] = True
                new["completedAt"] = now
            elif not done:
                new["completed"] = False
                new["completedAt"] = None
        new["updatedAt"] = now
        new["version"] = int(old.get("version", 0)) + 1
        new = _without_empty(new)
        new["completed"] = bool(new.get("completed"))
        new.update(index_keys(user_id, new))
        try:
            self._table.put_item(
                Item=new,
                ConditionExpression=Attr("PK").exists() & _same_version(old),
            )
        except ClientError as err:
            if not _is_condition_failure(err):
                raise
            if self._get_item(user_id, todo_id) is None:
                raise TodoNotFound from err
            raise TodoChanged from err
        return _detail(new)

    def delete(self, user_id: str, todo_id: str) -> None:
        try:
            self._table.delete_item(
                Key={"PK": user_pk(user_id), "SK": todo_sk(todo_id)},
                ConditionExpression=Attr("PK").exists(),
            )
        except ClientError as err:
            if _is_condition_failure(err):
                raise TodoNotFound from err
            raise

    def list_view(
        self,
        user_id: str,
        view: View,
        *,
        today: str,
        tomorrow: str,
        cursor: str | None = None,
        limit: int = PAGE_SIZE,
    ) -> tuple[list[dict[str, Any]], str | None]:
        rng = _range(user_id, view, today, tomorrow)
        partition = Key("GSI1PK").eq(rng.pk)
        condition = (
            partition & Key("GSI1SK").between(rng.low, rng.high)
            if rng.low is not None and rng.high is not None
            else partition
        )
        query: dict[str, Any] = {
            "IndexName": GSI1,
            "KeyConditionExpression": condition,
            "ScanIndexForward": not rng.newest_first,
            "Limit": limit,
        }
        if cursor:
            query["ExclusiveStartKey"] = decode_cursor(cursor, user_id, rng)
        response = self._table.query(**query)
        items = [_summary(item) for item in response.get("Items", [])]
        last = response.get("LastEvaluatedKey")
        return items, encode_cursor(last) if last else None
