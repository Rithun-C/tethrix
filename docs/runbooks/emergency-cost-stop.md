# Runbook: Emergency cost stop

Task: G-13.

## When to use it

- A Budgets alert email you did not expect
- Credits dropping faster than the Cost Log explains
- The sweep shows something you do not recognise
- You realise you forgot to destroy a lab

## The goal

Stop the spending first. Understand it second. Do not spend time investigating while
something is still running.

## Step 1: sign in (2 minutes)

```
aws login --profile admin
export AWS_PROFILE=admin
aws sts get-caller-identity --query Arn --output text
```

## Step 2: find what is running (5 minutes)

```
bash scripts/sweep.sh --all
```

Then, read-only in the Billing console: Bills, current month, charges by service. This shows
which service is spending, even for resources the sweep does not list.

## Step 3: stop it, most expensive first

Destroy with Terraform whenever the resource belongs to a stack:

```
cd infra/labs/<lab-name>      # or infra/envs/lab
terraform destroy
```

For anything Terraform does not know about, delete it with the CLI. Order: the most
expensive per hour first.

| Resource | Command |
|---|---|
| NAT gateway | `aws ec2 delete-nat-gateway --nat-gateway-id <id>` |
| EKS cluster | Delete node groups first: `aws eks delete-nodegroup ...`, then `aws eks delete-cluster --name <name>` |
| Load balancer | `aws elbv2 delete-load-balancer --load-balancer-arn <arn>` |
| RDS instance | `aws rds delete-db-instance --db-instance-identifier <id> --skip-final-snapshot --delete-automated-backups` |
| ECS service | `aws ecs update-service --cluster <c> --service <s> --desired-count 0`, then `aws ecs delete-service --cluster <c> --service <s>` |
| VPC endpoint | `aws ec2 delete-vpc-endpoints --vpc-endpoint-ids <id>` |
| EC2 instance | `aws ec2 terminate-instances --instance-ids <id>` |
| Elastic IP | `aws ec2 release-address --allocation-id <id>` |
| GuardDuty | `aws guardduty delete-detector --detector-id <id>` |
| Security Hub | `aws securityhub disable-security-hub` |
| Config | `aws configservice stop-configuration-recorder --configuration-recorder-name <name>` |
| Inspector | `aws inspector2 disable --resource-types EC2 ECR LAMBDA LAMBDA_CODE` |
| WAF web ACL | Remove it from CloudFront first (Terraform), then `aws wafv2 delete-web-acl ...` |

Add `--region <region>` if the resource is not in us-east-1.

Run the sweep again until it is clean.

## Step 4: was it a mistake, or someone else?

It is probably someone else if any of these are true:

- Resources in regions you never use
- An IAM user, role or access key you did not create
- Resource types you have never used (for example many large EC2 instances)

If so, treat it as a security incident:

1. Deactivate any access key you did not create:
   `aws iam update-access-key --user-name <user> --access-key-id <id> --status Inactive`
2. Change the admin password and check MFA is still on.
3. Find out who did it:

   ```
   aws cloudtrail lookup-events --max-results 50 \
     --query 'Events[].{time:EventTime,user:Username,event:EventName}' --output table
   ```

4. Open a free support case: Support Center, Account and billing, "Possible unauthorised
   activity".
5. The full leaked-key procedure is practised in the O-07 drill.

## Step 5: afterwards

- Cost Log: a row for the incident, with credits lost.
- Findings log: what happened and the fix.
- Journal: a short postmortem (what happened, why, what changes so it does not happen again).
- If a runbook or the sweep missed it, update them.

## Remember

On the Free plan you cannot be billed. The worst case is losing credits, which can close
the account early. Acting quickly limits that.
