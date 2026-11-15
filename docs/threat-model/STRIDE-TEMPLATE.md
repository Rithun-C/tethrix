# STRIDE threat model template

Copy this file to `threat-model.md` in Inception (task I-09) and keep it updated in every
bolt.

## Scope

- What is being modelled:
- Date and bolt:

## Data flow

Describe or draw how data moves: browser -> CloudFront -> Lambda -> DynamoDB / S3, and
where Cognito fits. Mark each trust boundary (the points where data crosses from a less
trusted place to a more trusted one).

## Assets

| Asset | Why it matters |
|---|---|
| Journal entries | Sensitive personal data |
| User credentials and tokens | Give access to everything a user owns |
| AWS credentials and deploy role | Give access to the account |

## Threats

One row per threat. STRIDE categories:

- Spoofing: pretending to be someone else
- Tampering: changing data or code
- Repudiation: denying an action because there is no record
- Information disclosure: reading data you should not see
- Denial of service: making the app unavailable (or burning credits)
- Elevation of privilege: gaining rights you should not have

| ID | Component | Category | Threat | Mitigation | Status | Verified by |
|---|---|---|---|---|---|---|
| T-001 | API | Information disclosure | User A reads user B's items (IDOR) | Every query scoped by the user ID from the verified JWT | Open | Two-user test |
| T-002 | Pages | Tampering | Stored XSS through rich-text content | Server-side schema validation, no raw HTML, CSP | Open | XSS payload tests |
| T-003 | Journal | Information disclosure | Journal text appears in logs | Log redaction; never log request bodies | Open | Log review |
| T-004 | Auth | Elevation of privilege | Local-dev auth bypass active in a deployed build | Bypass only compiled in for local; startup check | Open | Deploy test |

Status values: Open, Mitigated, Accepted (with reason).

## Review log

| Date | Bolt | What changed |
|---|---|---|
