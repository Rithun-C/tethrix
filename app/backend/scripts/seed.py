"""Writes made-up data for two users into DynamoDB Local.

Two users, so that every later test can ask: "can Alice see Bob's data?" (IDOR).
The data is invented. Real journal text never goes into seed files or tests.

Local only. Safe to run again: the same keys are simply written again.
"""

from typing import TYPE_CHECKING, Any

from api.config import get_settings
from api.db import get_table, user_pk
from local_table import require_local

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

# Fixed user IDs, so tests can refer to them. They are the names typed at the local
# sign-in page (the local OIDC server in Compose uses the typed name as the token's
# `sub`), so signing in locally as "alice" shows Alice's seed data (B4-05). In AWS the
# IDs are Cognito's UUIDs; the code treats both the same.
ALICE = "alice"
BOB = "bob"

_CREATED = "2026-11-01T09:00:00Z"


def _profile(user_id: str, time_zone: str) -> dict[str, Any]:
    return {"PK": user_pk(user_id), "SK": "PROFILE", "timeZone": time_zone, "createdAt": _CREATED}


def _todo(
    user_id: str,
    todo_id: str,
    title: str,
    *,
    due: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "PK": user_pk(user_id),
        "SK": f"TODO#{todo_id}",
        "todoId": todo_id,
        "title": title,
        "completed": completed_at is not None,
        "createdAt": _CREATED,
        "updatedAt": completed_at or _CREATED,
    }
    if due:
        item["dueDate"] = due
    # The index keys decide which list a todo shows up in (I-08, GSI1).
    if completed_at:
        item["completedAt"] = completed_at
        item["GSI1PK"] = f"{user_pk(user_id)}#TODO#DONE"
        item["GSI1SK"] = f"DONE#{completed_at}#{todo_id}"
    else:
        item["GSI1PK"] = f"{user_pk(user_id)}#TODO#OPEN"
        item["GSI1SK"] = f"DUE#{due}#{todo_id}" if due else f"NODUE#{todo_id}"
    return item


def seed_items() -> list[dict[str, Any]]:
    return [
        _profile(ALICE, "Asia/Kolkata"),
        _todo(ALICE, "a1", "Alice: water the plants", due="2026-11-20"),
        _todo(ALICE, "a2", "Alice: read one chapter"),
        _todo(ALICE, "a3", "Alice: pay the electricity bill", completed_at="2026-11-10T08:30:00Z"),
        _profile(BOB, "Europe/London"),
        _todo(BOB, "b1", "Bob: book the dentist", due="2026-11-18"),
        _todo(BOB, "b2", "Bob: clean the bike"),
    ]


def seed(table: "Table") -> int:
    items = seed_items()
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    return len(items)


def main() -> None:
    settings = get_settings()
    require_local(settings)
    count = seed(get_table(settings))
    print(f"Seeded {count} items for 2 users into {settings.dynamodb_table}")


if __name__ == "__main__":
    main()
