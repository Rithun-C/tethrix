# ADR-0005: Human admin identity

- Status: Accepted
- Date: 2026-11-11

Numbers 0002 to 0004 are reserved for the Inception ADRs.

## Context

Daily work must not use the root user. Root cannot be restricted by any policy, so a
stolen root login means losing the account. We need one human identity for console
(read-only billing checks) and CLI work, without long-lived access keys.

The project rule says no `*` in IAM policies unless an ADR justifies it. An admin
identity needs broad access, so this ADR is that justification.

## Options

### Option A: IAM Identity Center
- For: the AWS-recommended way to give people access; short-lived credentials by design.
- Against: giving Identity Center users access to an AWS account needs an organization
  instance, which needs AWS Organizations. Joining Organizations upgrades the account to
  the Paid plan. Not allowed.

### Option B: IAM user with access keys
- For: simple; works with every tool.
- Against: access keys are permanent secrets stored on disk. Leaked keys are the most
  common cause of AWS account breaches.

### Option C: IAM user with console password, MFA and `aws login`
- For: no long-lived keys. `aws login` gives the CLI temporary credentials through the
  browser sign-in, refreshed automatically. MFA protects the console login.
- Against: still an IAM user with a password; the admin policy is broad.

## Decision

Option C. One IAM user named `admin` with:

- Console password and MFA
- `AdministratorAccess` (AWS managed, `Action: *`, `Resource: *`)
- `SignInLocalDevelopmentAccess` (allows `aws login`)
- No access keys

Why `AdministratorAccess` is acceptable here: this is the single human operator of a
single-person account, and the operator must be able to create and destroy anything
Terraform manages. It is never used by code, CI or the app. Those get their own
least-privilege roles (CI roles in bolt B6).

This user was created in the console as the one-time bootstrap exception. It is not
managed by Terraform, because Terraform would then be able to delete the identity it
runs as.

## Consequences

- The real protections are MFA and the absence of access keys. If either changes, revisit
  this ADR.
- Never create access keys for `admin`. Prowler (G-11, O-05) should confirm this.
- Bolt B11-07 looks again at narrowing this with a permission boundary.

## What I learned

To be filled in by the owner.
