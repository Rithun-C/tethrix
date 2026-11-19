# Module: dynamodb_table

The app's single table from I-08: keys `PK`/`SK`, index `GSI1` (`GSI1PK`/`GSI1SK`, only
list fields copied), provisioned capacity, point-in-time recovery, encryption and
deletion protection on. Task B3-03.

| Input | Default | Meaning |
|---|---|---|
| `name` | | Table name |
| `table_capacity` | 10 | Read and write units of the table |
| `index_capacity` | 5 | Read and write units of the index (1 to 10) |
| `deletion_protection` | true | Set to false only for the final destroy |

Outputs: `name`, `arn`, `index_arns`.

The local copy of this layout is `app/backend/scripts/local_table.py`. Change both
together.
