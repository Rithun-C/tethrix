# Threat model

- Status: v1 Approved 2026-11-15
- Date: 2026-11-15
- Task: I-09. Updated in every bolt (Definition of Done).
- Based on: `docs/inception/10-architecture-diagrams.md` (trust boundaries TB1 to TB4)

## 1. What a threat model is

A threat model answers four questions, before anything is built:

```mermaid
flowchart LR
  q1["1 What are we building?<br/>(diagrams, data)"] --> q2["2 What can go wrong?<br/>(STRIDE, per component)"]
  q2 --> q3["3 What do we do about it?<br/>(mitigate, accept, avoid)"]
  q3 --> q4["4 Did we do a good job?<br/>(tests, scans, review)"]
  q4 -. "every bolt" .-> q1
```

STRIDE is a checklist for question 2. For each part of the system, ask whether an attacker
could:

```mermaid
flowchart TB
  A([Attacker]) --> S["<b>S</b>poofing<br/>pretend to be someone else"]
  A --> T["<b>T</b>ampering<br/>change data or code"]
  A --> R["<b>R</b>epudiation<br/>do something with no record"]
  A --> I["<b>I</b>nformation disclosure<br/>read what they should not"]
  A --> D["<b>D</b>enial of service<br/>break it, or burn the credits"]
  A --> E["<b>E</b>levation of privilege<br/>gain more power"]
```

Each STRIDE letter breaks one security property: S breaks authentication, T integrity,
R accountability, I confidentiality, D availability, E authorization.

For each threat we choose one response:

| Response | Meaning | Example here |
|---|---|---|
| Mitigate | Add a control that blocks or limits it | Token checks, input validation |
| Accept | Live with it, with a written reason | A signed-out token works until it expires (max 60 min) |
| Avoid | Remove the feature that causes it | No public sign-up, no sharing |
| Transfer | Let someone else carry it | AWS runs the data centres (shared responsibility) |

## 2. What we are protecting (assets)

| Asset | Why it matters | Worst case |
|---|---|---|
| Journal entries | Sensitive personal thoughts | Read by someone else |
| Pages, todos, habits | Personal data | Read or changed by someone else |
| User accounts and tokens | Access to everything a user owns | Account takeover |
| AWS account (admin, deploy role) | Controls all infrastructure and data | Data deleted or exposed; credits burned |
| Credits (200 USD) | The account closes at zero | Project ends early |
| Terraform state | Records every resource; may hold sensitive values | Infrastructure lost or exposed |

## 3. Where the threats sit

The main threats placed on the trust boundary diagram from I-10. Each arrow crossing a
boundary is a place an attacker can push on.

```mermaid
flowchart LR
  subgraph internet [Untrusted: the internet]
    user([Browser])
    attacker([Attacker])
  end

  subgraph aws [AWS account]
    cf[CloudFront]
    lambda[Lambda FastAPI]
    ddb[(DynamoDB)]
    cognito[Cognito]
    logs[(CloudWatch logs)]
  end

  gh[GitHub Actions]

  user -- "TB1<br/>T-001 forged token<br/>T-006 XSS content<br/>T-007 bad input<br/>T-021 flood" --> cf
  attacker -. "TB2<br/>T-002 skip CloudFront" .-> lambda
  cf --> lambda
  lambda -- "TB3<br/>T-013 IDOR<br/>T-024 role too wide" --> ddb
  lambda -- "T-014 journal in logs" --> logs
  user -- "TB4<br/>T-003 stolen password" --> cognito
  gh -- "T-005, T-025<br/>deploy role misuse<br/>T-008 bad dependency" --> aws
```

## 4. Threats

Risk = how likely x how bad, before the mitigation: High, Medium or Low.
Status: Planned (mitigation designed, not built yet), Done, Accepted.

### Spoofing

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-001 | API (TB1) | Forged, expired or another app's JWT accepted | High | Full JWT checks: signature via JWKS, RS256 only, issuer, expiry, `token_use`, `client_id` (ADR-0003) | Unit tests with bad tokens | B4 | Planned |
| T-002 | Lambda (TB2) | Attacker calls Lambda directly, skipping the front door | Medium | No function URL; the only resource policy lets our API Gateway invoke the function (ADR-0007, SR-62) | Terraform review; `make smoke` reaches the app only through API Gateway | B3 | Planned |
| T-003 | Sign-in (TB4) | Stolen or guessed password | High | MFA required (TOTP); 14-character passwords; Cognito lockout | Manual test; Cognito settings in Terraform | B4 | Planned |
| T-004 | Local auth | Local-dev token mode active in AWS | High | Refuses to start in Lambda; never set by Terraform | Unit test | B4 | Planned |
| T-005 | CI/CD | Another repo or branch assumes the deploy role | High | OIDC trust pinned to this repo and environment | Policy review, Access Analyzer | B6 | Planned |

### Tampering

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-006 | Pages | Stored XSS: saved content runs script in the browser | High | Server checks content matches the editor schema; no raw HTML rendering; strict CSP; safe link handling (US-42) | XSS payload test list | B8 | Planned |
| T-007 | API input | Oversized or malformed input | Medium | Validation on every field; body size limit; 400 errors | Unit tests | B5 onward | Planned |
| T-008 | Supply chain | Malicious or vulnerable dependency or base image | High | Exact pins and lockfiles; image digests; pip-audit, npm audit, Trivy in CI; check every new package is the real one | CI gates | B1, B6 | Done (B1: pins, digests, Trivy. B2: pip-audit, npm audit, install scripts off, cooldowns) |
| T-009 | Terraform state | State changed or deleted | Medium | Private, versioned, encrypted bucket; HTTPS only; locking; `prevent_destroy` | Done in G-06 | G-06 | Done |
| T-010 | Pages, journal | Two tabs silently overwrite each other | Low | Optimistic concurrency, 409 on conflict (I-03) | Unit test | B8 | Planned |

### Repudiation

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-011 | AWS account | Changes to infrastructure with no record | Medium | CloudTrail, all regions, log file validation | Done in G-09; `validate-logs` passed | G-09 | Done |
| T-012 | App | API actions with no record | Low | Structured logs per request: request ID, user `sub`, endpoint, status. Never content. Log retention set | Log review | B3 onward | Planned |

### Information disclosure

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-013 | API, DynamoDB (TB3) | IDOR: user A reads user B's data | High | Every key built from the token's `sub`; one partition per user; 404 for others' items (I-08) | Two-user test for every endpoint | B4 onward | Planned |
| T-014 | Logs, errors | Journal text appears in logs, traces or error messages | High | Never log request or response bodies; redaction; generic errors (US-33) | Test that greps logs for a marker string | B8 | Planned |
| T-015 | Browser | Tokens stolen through an XSS bug | Medium | Access token in memory only; short lifetimes; CSP; XSS defences (T-006) | Review | B4 | Accepted (residual risk, see ADR-0003) |
| T-016 | Repo | Secret, key or account ID committed to the public repo | High | gitleaks in pre-commit and CI; no secrets in code; Parameter Store for any secret | CI gate | B1 | Done |
| T-017 | API errors | Stack traces or internals shown to users | Medium | One error handler; 500 responses carry no details | Unit test | B3 | Planned |
| T-018 | Data at rest | Stored data read from disks or backups | Low | DynamoDB and S3 encrypted by default; journal encryption ADR | Settings in Terraform | B8 | Planned |
| T-019 | Export | Export contains another user's data, or its file leaks | Medium | Export built only from the caller's partition; short-lived link if S3 is used | Two-user test | B9 | Planned |
| T-020 | Browser | Clickjacking or content-type tricks | Low | Security headers: CSP `frame-ancestors 'none'`, `X-Content-Type-Options`, HSTS, `Referrer-Policy` | Header check | B3 | Planned |

### Denial of service (including "denial of wallet")

On the Free plan, an attack that makes us spend credits is as damaging as one that takes
the app down.

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-021 | API | Request flood burns credits | Medium | API Gateway throttling (10 a second, bursts of 20) refuses a flood with 429 before Lambda runs (ADR-0007); DynamoDB provisioned capacity caps cost; Lambda concurrency limit; budgets alert | Load test in B11-08 | B3, B11 | Planned |
| T-022 | API | Expensive requests: huge bodies, unbounded lists | Medium | Size limits; pagination (max 50); 10-second Lambda timeout | Unit tests | B5 onward | Planned |
| T-023 | AWS account | Forgotten lab resources | Medium | Session sweep, emergency runbook, budgets | Done in G-07, G-12, G-13 | Week 0 | Done |

### Elevation of privilege

| ID | Where | Threat | Risk | Mitigation | Verified by | Bolt | Status |
|---|---|---|---|---|---|---|---|
| T-024 | Lambda role (TB3) | Code bug used to do more than the app needs | Medium | Lambda role allows only the needed DynamoDB actions on our table ARN; no `*` | Access Analyzer `validate-policy` | B3 | Planned |
| T-025 | CI/CD | Deploy role does more than deploy | High | Separate read-only plan role and apply role; scoped actions | Access Analyzer, review | B6 | Planned |
| T-026 | Admin user | Admin login stolen | High | MFA, no access keys, `aws login` temporary credentials (ADR-0005) | Prowler | G-04 | Done |
| T-027 | Sessions | A signed-out user's access token still works | Low | Lifetime 60 minutes; account deletion is enforced by the profile check | Unit test | B4 | Accepted (max 60 minutes) |
| T-028 | CI/CD | A pull request from a fork runs malicious code in our CI | Medium | `pull_request` trigger only (never `pull_request_target`); read-only token; no secrets in CI; approval required before an outside contributor's workflow runs; actions pinned by SHA | Workflow review; GitHub settings (runbook `repo-and-ci.md`) | B1 | Done |
| T-029 | Local dev | Local dev services reachable from the network; DynamoDB Local has no sign-in | Low | Every Compose port bound to `127.0.0.1`; seed data is made up; real data never local | Review of `compose.yaml` | B2 | Done |
| T-030 | Images | A secret or private file is baked into an image layer | Medium | Allow-list `.dockerignore`; no secrets as build arguments; Trivy secret scan of the built image in CI | CI gate (`make image-scan`) | B2 | Done |
| T-031 | Containers | A compromised container has more power than the app needs | Low | Non-root user, read-only file system, all capabilities dropped, `no-new-privileges`, final image without build tools | hadolint, checkov; review | B2 | Done |
| T-032 | DNS | Subdomain takeover: the Route 53 zone is deleted while the NS records for `tethrix` still exist at `satrix.in`, and someone else claims the name | Medium | Destroy order in the runbook: NS records at the parent are removed first; CAA record allows only Amazon to issue certificates | Runbook `deploy-manual.md`, "Undo" | B3 | Planned |
| T-033 | API | The API is public with no sign-in until B4 | Low | Only health and the byte-count echo exist; no data; body limit, 10 s timeout, account concurrency limit, budgets | `make smoke`; route list test | B3 | Planned |
| T-034 | Images | A wrong or vulnerable image reaches Lambda | Medium | Trivy scan of the exact image before push; immutable tags tied to commit IDs; push refused with uncommitted changes; ECR scan on push | `make push-backend` | B3 | Planned |
| T-036 | Transport | While the app is on the default `execute-api` address, TLS settings are AWS's defaults, not our TLS 1.2 policy | Low | Temporary (ADR-0006 update, ADR-0007): ends when the custom domain with `TLS_1_2` is switched on and the default address is turned off. Browsers negotiate TLS 1.3; HSTS keeps them on HTTPS | `make smoke` runs the TLS 1.1 check once the domain is on | B3 | Accepted (until the domain) |
| T-035 | Frontend files | The React files are changed or other files are read | Medium | No bucket any more (ADR-0007): the files are inside the immutable, scanned backend image in ECR. Only the admin can push images | Image scan on push; tags immutable | B3 | Planned |
| T-037 | Static files | Path traversal through static file serving (`/assets/../../etc/passwd`) reads files from the container | Medium | Starlette `StaticFiles` refuses paths outside its folder; read-only file system in Lambda; no secrets in the image (T-030) | `tests/test_static.py` (three encodings); `make smoke` | B3 | Planned |
| T-038 | Transport | The default `execute-api` address bypasses the custom domain and its TLS policy | Low | `disable_execute_api_endpoint` follows `use_custom_domain` | `make smoke` checks the default address is off once the domain is on | B3 | Planned |

## 5. Summary

| | High | Medium | Low | Total |
|---|---|---|---|---|
| Threats | 11 | 17 | 10 | 38 |
| Already done (Week 0) | | | | 4 |
| Done in B1 (T-008 in part, T-016, T-028) | | | | 3 |
| Done in B2 (T-029, T-030, T-031) | | | | 3 |
| Added in B3, done after the first deploy (T-032 to T-035, T-037, T-038) | | | | 0 |
| Accepted in B3 until the custom domain (T-036) | | | | 1 |
| Accepted with reason | | | | 2 |

The High risks that need the most care: IDOR (T-013), stored XSS (T-006), journal text in
logs (T-014), JWT checks (T-001), supply chain (T-008) and the CI deploy role (T-005, T-025).

## Review log

| Date | Bolt | What changed |
|---|---|---|
| 2026-11-15 | Inception | v1: 27 threats from the I-10 diagrams |
| 2026-11-15 | B1 | T-028 added (fork pull request runs code in CI). T-008 and T-016 controls written; they move to Done when B1 closes |
| 2026-11-15 | B1 closed | T-016 and T-028 Done, verified on GitHub (ruleset, push protection, fork approval, failing pull request blocked). T-008 done for what exists; package audits follow in B2 |
| 2026-11-15 | B2, pull request 1 | T-029, T-030 and T-031 added and mitigated (local ports, secrets in images, container rights). T-008: pip-audit now runs in CI; npm audit follows with the frontend |
| 2026-11-15 | B2, pull request 2 | T-008: npm audit now runs in CI and npm install scripts are off, so every planned control is in place. No new threats from the frontend skeleton: it has no user input and no stored data yet |
| 2026-11-15 | B2, pull request 3 | Reviewed for the kind lab: no new threats. The cluster exists only on the laptop for the length of the lab, holds made-up data and is reached only through a port-forward on localhost. The lab practises the T-031 controls in Kubernetes form (Pod Security "restricted", network policies). Manifests are now scanned by checkov |
| 2026-11-20 | B3, pull requests 1 and 2 | T-032 to T-035 added (subdomain takeover, public API before sign-in, image supply, frontend bucket). The custom domain (ADR-0006) removes the old-TLS gap that the design had expected. T-002, T-020, T-021, T-024 controls written in Terraform; they move to Done when `make smoke` passes after the deploy |
| 2026-11-20 | B3, API Gateway (ADR-0007) | CloudFront is not enabled for this account, so API Gateway is the front door and FastAPI serves the React files. T-002 (no function URL), T-021 (throttling), T-035 (no bucket), T-036 (default execute-api address) rewritten; T-037 (path traversal) and T-038 (default address bypass) added |
| 2026-11-20 | B3, default-domain fallback | The parent domain is on hold, so B3 deploys on the `*.cloudfront.net` address first. T-036 added and accepted until the domain is switched on. T-032 applies only once the domain is on |
