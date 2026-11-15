# Theory notes

Topics that cannot be practised on the Free plan, or that need background before the
practical work. One file per topic, written when the linked task comes up.

Each note answers: what it is, what problem it solves, how it works, what it costs, when
you would use it, and why we are not using it here.

## Theory only (cannot be practised here)

| Topic | Why not practical | Task |
|---|---|---|
| AWS Organizations and SCPs | Joining upgrades the account to Paid | B11-09 |
| Control Tower | Same as above | B11-09 |
| EKS | Hourly control-plane cost; Kubernetes is practised locally with kind | B2-08 |
| NAT Gateway | Hourly cost plus data charges | B3-10 |
| Transit Gateway | Hourly cost; needs several VPCs | B11-10 |
| Network Firewall | Hourly cost | B11-10 |
| Shield Advanced | Subscription cost | B11-10 |
| Multi-region disaster recovery | One-region rule | B11-10 |

## Background notes that go with practical work

| Topic | Task |
|---|---|
| Free plan mechanics, shared responsibility, IAM fundamentals: [free-plan-shared-responsibility-iam.md](free-plan-shared-responsibility-iam.md) | G-14 |
| Well-Architected pillars; Lambda vs ECS vs EKS: [well-architected-and-compute.md](well-architected-and-compute.md) | I-14 |
| Terraform basics, explained through G-06: [terraform-basics.md](terraform-basics.md) | G-06 |
| Terraform state, locking, drift, modules: [terraform-state-and-modules.md](terraform-state-and-modules.md) | B1-08 |
| Supply-chain security: [supply-chain-security.md](supply-chain-security.md) | B1-09 |
| Container internals and image hardening | B2-08 |
| CloudFront, OAC vs OAI, SigV4 | B3-09 |
| VPC basics; why this Lambda is outside a VPC | B3-10 |
| The default VPC: what it is, why deleting it is good practice, why we keep it for the EC2 lab | B3-10 |
| OAuth2/OIDC, JWT pitfalls, user pools vs identity pools | B4-07 |
| Backend-for-frontend (BFF): tokens in cookies instead of the browser (ADR-0003) | B4-07 |
| Lambda Web Functions (Node.js only; rejected in ADR-0002) | B3-09 |
| DynamoDB keys, GSIs, capacity modes | B5-06 |
| OIDC federation, deployment strategies, AWS Code* services | B6-08 |
| KMS envelope encryption; Parameter Store vs Secrets Manager | B8-09 |
| S3 security deep dive; event-driven patterns | B10-07 |
| S3 Object Lock (write-once logs) and why we do not enable it here | B10-07 |
| CloudTrail Insights, CloudTrail Lake, data events | O-04 |
| Security alerting (F-008): CloudWatch metric filters and alarms vs free EventBridge rules to SNS | O-01 |
| Access Analyzer unused access and internal access analyzers (paid) | B11-07 |
| Incident response lifecycle; RPO and RTO | O-13 |
