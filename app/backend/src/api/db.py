"""Access to the one DynamoDB table (I-08).

Keys are built here and nowhere else. Every key of a user's item starts with
USER#<user id>, and the user id always comes from the verified token (SR-20), never
from the request. No function here takes a key from outside.
"""

from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from api.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

GSI1 = "GSI1"

# Short timeouts and few retries: Lambda stops a request after 10 seconds (ADR-0004),
# so waiting long for the database only burns that time.
_CLIENT_CONFIG = Config(
    connect_timeout=2,
    read_timeout=3,
    retries={"max_attempts": 3, "mode": "standard"},
)


def dynamodb_resource(settings: Settings) -> "DynamoDBServiceResource":
    # endpoint_url is None in AWS: the SDK then uses the real DynamoDB of the region.
    return boto3.resource(
        "dynamodb",
        endpoint_url=settings.dynamodb_endpoint_url,
        config=_CLIENT_CONFIG,
    )


def get_table(settings: Settings) -> "Table":
    return dynamodb_resource(settings).Table(settings.dynamodb_table)


def user_pk(user_id: str) -> str:
    """Partition key: all of one user's items live under it."""
    return f"USER#{user_id}"
