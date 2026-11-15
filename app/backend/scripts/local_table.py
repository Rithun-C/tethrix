"""Creates the DynamoDB table in DynamoDB Local, as designed in I-08.

Local only. In AWS the table is created by Terraform (B3), never by a script.
Run through Docker Compose: `make up` does it; safe to run again.
"""

import sys
import time
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError, EndpointConnectionError

from api.config import Settings, get_settings
from api.db import GSI1, dynamodb_resource

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource


def require_local(settings: Settings) -> None:
    """Stop unless we are pointed at DynamoDB Local.

    Without this, running the script with real AWS credentials in the terminal would
    create a table (or write seed data) in the real account.
    """
    if settings.dynamodb_endpoint_url is None:
        sys.exit("Refusing to run: DYNAMODB_ENDPOINT_URL is not set. This script is local only.")


def wait_until_ready(dynamodb: "DynamoDBServiceResource", seconds: int = 30) -> None:
    """DynamoDB Local needs a moment after its container starts."""
    deadline = time.monotonic() + seconds
    while True:
        try:
            dynamodb.meta.client.list_tables()
            return
        except (EndpointConnectionError, ClientError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


def create_table(dynamodb: "DynamoDBServiceResource", name: str) -> bool:
    """Create the table. Returns False if it was already there."""
    try:
        table = dynamodb.create_table(
            TableName=name,
            # Only key fields are declared. DynamoDB has no fixed columns for the rest.
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},  # HASH = partition key
                {"AttributeName": "SK", "KeyType": "RANGE"},  # RANGE = sort key
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": GSI1,
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    # The index copies only what lists show, not notes or page content.
                    "Projection": {
                        "ProjectionType": "INCLUDE",
                        "NonKeyAttributes": ["title", "dueDate", "priority", "completed"],
                    },
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                }
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        )
    except ClientError as err:
        if err.response.get("Error", {}).get("Code") == "ResourceInUseException":
            return False
        raise
    table.wait_until_exists()
    return True


def main() -> None:
    settings = get_settings()
    require_local(settings)
    dynamodb = dynamodb_resource(settings)
    wait_until_ready(dynamodb)
    created = create_table(dynamodb, settings.dynamodb_table)
    print(f"Table {settings.dynamodb_table}: {'created' if created else 'already exists'}")


if __name__ == "__main__":
    main()
