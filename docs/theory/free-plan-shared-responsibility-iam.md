# Free plan, shared responsibility and IAM fundamentals

Task: G-14. Written 2026-11-12 after the Week 0 guardrails, so every idea links to
something already built.

## 1. The AWS Free plan

### What it is

Since July 2025, a new AWS account picks a plan:

| | Free plan | Paid plan |
|---|---|---|
| Credits | 100 USD at sign-up, up to 100 USD more from activities | Same |
| Can you be charged? | No | Yes, once credits run out |
| Services | A selected set; some costly ones are blocked | Everything |
| End | After 6 months, or when credits run out | Never |

This account: Free plan, 200 USD (100 sign-up + 100 from the five G-03 activities), ends
2027-05-11.

### What happens at the end

1. AWS emails you 15, 7 and 2 days before.
2. The account closes. You lose access to resources and data.
3. AWS keeps everything for 90 days. Upgrading to Paid within that time reopens it.
4. After 90 days, the account and everything in it is deleted.

Our plan: export data, destroy everything by 2027-04-30, and let it close.

### What upgrades you to Paid without asking

Joining AWS Organizations, setting up Control Tower, joining the Partner Network,
certain contracts and compliance designations. Upgrading cannot be undone. This is why
Organizations is forbidden here.

### Why credits matter more than money

On the Free plan you cannot get a bill. The real risk is different: every hour a costly
resource runs, credits disappear, and at zero the account closes, possibly months early.
That is why we have budgets (G-07), the sweep (G-12) and the emergency runbook (G-13).

## 2. The shared responsibility model

AWS and you split the security work.

- AWS is responsible for security **of** the cloud: data centres, hardware, the network,
  and the software that runs each service.
- You are responsible for security **in** the cloud: who has access, how resources are
  configured, your data and your code.

The split moves depending on how managed a service is:

| You manage... | EC2 (a server) | Lambda (a function) | S3 / DynamoDB (storage) |
|---|---|---|---|
| Physical security, hardware | AWS | AWS | AWS |
| Operating system patches | **You** | AWS | AWS |
| Runtime (Python version etc.) | **You** | Shared: you pick, AWS patches | n/a |
| Network rules (security groups) | **You** | Mostly AWS (outside a VPC) | n/a |
| Your code | **You** | **You** | n/a |
| IAM permissions | **You** | **You** | **You** |
| Data and its encryption settings | **You** | **You** | **You** |

Two lessons:

- The more managed the service, the less you can get wrong. This is one reason the app
  runs on Lambda and DynamoDB, not EC2.
- IAM and data protection are always yours. Almost every real cloud breach is a
  customer-side mistake: a public bucket, a leaked key, a policy with `*`. Not a failure
  of AWS.

Where Week 0 fits: every guardrail you built is on your side of the line. AWS will not
turn on MFA, block public buckets or record CloudTrail for you.

## 3. IAM fundamentals

IAM (Identity and Access Management) answers one question for every request:
**who** is asking to do **what** to **which resource**, and is it allowed?

### Who: principals

| Principal | What it is | In this account |
|---|---|---|
| Root user | The account owner. Can do anything, cannot be restricted | Locked away with MFA (G-01) |
| IAM user | A named, long-term identity with a password and/or keys | `admin` (G-04) |
| IAM role | An identity with no password or keys. You assume it and get temporary credentials | `security-audit` (G-11) |
| Service principal | An AWS service acting for you, such as `cloudtrail.amazonaws.com` | CloudTrail writing logs (G-09) |

Prefer roles. Temporary credentials expire on their own, so a leak does limited damage.

### What and which: policies

A policy is a JSON document of statements. Each statement says:

```
Effect:    Allow or Deny
Action:    what can be done, e.g. s3:GetObject
Resource:  which thing, by ARN, e.g. arn:aws:s3:::my-bucket/*
Condition: optional extra rules, e.g. only over HTTPS
```

Types of policy used so far:

| Type | Attached to | Answers | Example |
|---|---|---|---|
| Identity policy | A user or role | "What may this identity do?" | `AdministratorAccess` on admin |
| Resource policy | A resource | "Who may use this resource?" | The CloudTrail bucket policy |
| Trust policy | A role | "Who may assume this role?" | `security-audit` trusts only admin |

### How AWS decides

1. Everything starts as **denied**. Nothing is allowed unless a policy allows it.
2. If any applicable policy says **Allow**, the request may be allowed.
3. If any applicable policy says **Deny**, the request is denied. An explicit Deny always
   wins over any Allow.

Example from G-06: the state bucket policy denies all requests not over HTTPS. Even
`admin`, whose policy allows everything, cannot read the bucket over plain HTTP, because
the explicit Deny wins.

### Credentials

| Kind | Lifetime | Used here |
|---|---|---|
| Password + MFA | Long-term | Console sign-in for admin |
| Access keys | Long-term, until deleted | None. Deliberately (ADR-0005) |
| Temporary credentials | Minutes to hours | `aws login`, the `audit` profile, GitHub OIDC later |

### Least privilege

Give each identity only the permissions its job needs. Applied so far:

- Prowler uses a read-only role, not admin.
- CloudTrail may only write to its own folder in the bucket, and only for our trail.
- Our IAM policies have no `*` unless an ADR justifies it (ADR-0005 is the one exception).

## 4. Check your understanding

1. Why can't AWS send you a bill on this account, and what is the real risk instead?
2. Who patches the operating system for a Lambda function? For an EC2 instance?
3. `admin` has `AdministratorAccess`. Why can it still not read the state bucket over HTTP?
4. Why is a role with temporary credentials safer than a user with access keys?
5. What would happen if the `security-audit` trust policy allowed `"AWS": "*"`?
