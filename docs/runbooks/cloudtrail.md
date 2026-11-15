# Runbook: CloudTrail

Task: G-09. Stack: `infra/bootstrap/`. Code: `cloudtrail.tf`.

## Purpose

Create a trail that records every management action in every region, delivered to a
private S3 bucket, with log file validation on.

## Prerequisites

- G-08 done
- Signed in: `aws login --profile admin`

## Steps

```
cd infra/bootstrap
export AWS_PROFILE=admin
terraform plan -out=tfplan
```

Check the plan before applying:

- Summary line: `Plan: 8 to add, 0 to change, 0 to destroy.`
- 7 resources named `aws_s3_bucket*.cloudtrail` and 1 named `aws_cloudtrail.this`.
- In `aws_cloudtrail.this`: `is_multi_region_trail = true`,
  `enable_log_file_validation = true`, `include_global_service_events = true`.
- Nothing else changes.

If the plan looks right:

```
terraform apply tfplan
rm tfplan
```

## Verify

Set two shell variables first, so the commands below stay short:

```
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET=productivity-app-cloudtrail-$ACCOUNT
```

1. The trail is recording:

   ```
   terraform plan                                                    # "No changes."
   aws cloudtrail get-trail-status --name productivity-app-trail \
     --query '{logging:IsLogging,lastDelivery:LatestDeliveryTime,error:LatestDeliveryError}'
   ```

   `logging` must be `true`. `error` must be empty.

2. Log files arrive. The first ones take 5 to 15 minutes:

   ```
   aws s3 ls s3://$BUCKET/AWSLogs/$ACCOUNT/CloudTrail/ --recursive | head
   ```

3. Digest files arrive. The first one takes about an hour:

   ```
   aws s3 ls s3://$BUCKET/AWSLogs/$ACCOUNT/CloudTrail-Digest/ --recursive | head
   ```

4. The logs have not been tampered with. Run this at least an hour after the apply.
   Replace the start time with a time just after your apply, in UTC:

   ```
   aws cloudtrail validate-logs \
     --trail-arn "arn:aws:cloudtrail:us-east-1:${ACCOUNT}:trail/productivity-app-trail" \
     --start-time 2026-11-12T00:00:00Z
   ```

   It must report the files as valid.

   Note: write `${ACCOUNT}` with braces. In zsh (the macOS shell), `$ACCOUNT:t` is read
   as a special "tail" modifier, which silently eats the `:t` of `:trail`.

## Practice: read the logs from the CLI

Event history is free and covers the last 90 days. Try these:

```
# Who created the trail, and when?
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateTrail \
  --query 'Events[].{time:EventTime,user:Username,event:EventName}' --output table

# Your recent console sign-ins
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --max-results 5 \
  --query 'Events[].{time:EventTime,user:Username}' --output table

# Everything the admin user did recently
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=admin \
  --max-results 20 \
  --query 'Events[].{time:EventTime,event:EventName,source:EventSource}' --output table
```

The output contains your account ID and IP address. Fine to read, not to commit.

## How to undo

Not planned before the end of the project. The bucket cannot be deleted while it holds
logs, which is intentional. O-11 empties it first.

## Cost

Management events from the first trail are free. S3 storage for a few MB of logs a month
is well under 0.05 USD.
