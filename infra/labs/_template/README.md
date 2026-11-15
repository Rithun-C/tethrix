# Lab: NAME

- Bolt / task:
- Date:
- Status: Planned | Approved | Running | Destroyed | Theory only

## 1. Goal

What this lab teaches, in one or two sentences.

## 2. Before the lab

Nothing is applied until every line here is filled in.

| Check | Result |
|---|---|
| Remaining credits (from the billing page) | USD |
| Above the 50 USD reserve? | yes / no (if no: stop, write theory instead) |
| Lab budget used so far, of 40 USD | USD |
| Free plan check: is the service available, and how was that confirmed (dry run, error message, AWS docs) | |

## 3. Cost estimate

Prices from the AWS pricing page for us-east-1, read on DATE.

| Costly part | Price per hour | Hours | Cost |
|---|---|---|---|
| | | | |
| Total | | | |

## 4. Time box

- Start:
- Must be destroyed by (clock time, same day):

## 5. Approval

- Owner approved: yes / no
- Date:

## 6. Steps

```sh
cp backend.hcl.example backend.hcl   # then replace ACCOUNT_ID
AWS_PROFILE=admin terraform init -backend-config=backend.hcl
AWS_PROFILE=admin terraform plan
AWS_PROFILE=admin terraform apply
```

What to do and what to look at while it runs.

## 7. After the lab

| Check | Result |
|---|---|
| `terraform destroy` finished without errors | |
| `make sweep` is clean | |
| Actual time running | |
| Cost Log row added in the tracker | |
| Balance rechecked the next day | |

## 8. What I learned
