# The app's single DynamoDB table, as designed in I-08 (ADR-0001).
# The same layout is created locally by app/backend/scripts/local_table.py; keep the two
# in step.

resource "aws_dynamodb_table" "this" { # nosemgrep: terraform.aws.security.aws-dynamodb-table-unencrypted.aws-dynamodb-table-unencrypted
  #checkov:skip=CKV_AWS_119:Default AWS-owned encryption instead of a KMS key, project cost rule. Journal encryption is decided by ADR in B8.
  #checkov:skip=CKV2_AWS_16:No auto scaling on purpose: fixed provisioned capacity inside the free tier is the cost cap (ADR-0001, T-021).
  name         = var.name
  billing_mode = "PROVISIONED"

  # Fixed capacity: requests above it are throttled instead of billed. With the index
  # this stays inside the free tier of 25 read and 25 write units (I-11).
  read_capacity  = var.table_capacity
  write_capacity = var.table_capacity

  hash_key  = "PK" # partition key: which user (or item group) the item belongs to
  range_key = "SK" # sort key: which item, sorted inside the partition

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # A second way to look items up (for example todos by due date). It copies only the
  # fields lists show, not notes or page content.
  global_secondary_index {
    name               = "GSI1"
    projection_type    = "INCLUDE"
    non_key_attributes = ["title", "dueDate", "priority", "completed"]
    read_capacity      = var.index_capacity
    write_capacity     = var.index_capacity

    key_schema {
      attribute_name = "GSI1PK"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "GSI1SK"
      key_type       = "RANGE"
    }
  }

  # Continuous backup for the last 35 days (B3 decision 4). The data includes the
  # journal, which cannot be recreated.
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest is always on in DynamoDB; this states it in code (SR-51).
  server_side_encryption {
    enabled = true
  }

  # Refuses delete and destroy. Turned off on purpose only for the final destroy.
  deletion_protection_enabled = var.deletion_protection
}
