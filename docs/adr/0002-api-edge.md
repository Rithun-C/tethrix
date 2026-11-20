# ADR-0002: API edge (how requests reach the backend)

- Status: Superseded by ADR-0007 on 2026-11-20 (CloudFront is not enabled for this account on the Free plan). Accepted 2026-11-15
- Date: 2026-11-15
- Task: I-05

## Context

The browser loads the React app from CloudFront and calls the API under `/api/*` on the
same CloudFront domain. Something has to carry those API requests to the FastAPI code in
Lambda.

Requirements:

- Cost close to 0 USD when idle; no hourly charges.
- The backend can only be reached through CloudFront, so there is one front door (and
  WAF can be added there in the B11 lab).
- Works with a Python (FastAPI) backend and with Terraform provider 6.71.0.

Using the same domain for the app and the API also means the browser treats them as one
site, so no CORS setup is needed.

## Options

### Option A: CloudFront → Lambda function URL, locked with OAC

A function URL is a built-in HTTPS address for one Lambda function. With auth type
`AWS_IAM`, it only accepts requests signed with AWS credentials. Origin Access Control
(OAC) makes CloudFront sign every request it forwards, and a Lambda permission says
"only this CloudFront distribution may call this function".

- For: no extra service and no extra cost (Lambda and CloudFront free tiers); calling the
  function URL directly is impossible, because unsigned requests are rejected; teaches
  SigV4 request signing and resource policies.
- Against, two quirks:
  1. OAC puts its signature in the `Authorization` header, replacing whatever the browser
     sent. The user's sign-in token must travel in a different header (ADR-0003).
  2. Lambda does not accept unsigned request bodies. For requests with a body (POST, PUT,
     PATCH), the browser must send the SHA-256 hash of the body in the
     `x-amz-content-sha256` header. This is a few lines in the frontend API client.
- Limits: 6 MB request and response; up to 15 minutes per request.
- Cost: 0 USD.

### Option B: CloudFront → API Gateway HTTP API → Lambda

API Gateway is a managed API front end. Its HTTP API type has a built-in JWT authorizer
that checks Cognito tokens before Lambda runs.

- For: the normal `Authorization` header works; token checks happen before the code
  runs (defence in depth); per-route throttling; no body hashing.
- Against: an extra service to learn and secure; the API Gateway address stays public, so
  requests can skip CloudFront unless more work is done (a secret header check, or a
  custom domain); about 1 USD per million requests, with no free allowance confirmed for
  the Free plan; 30-second timeout.
- Cost: cents a month at our volume.

### Option C: CloudFront → Lambda Web Function, with OAC

Lambda Web Functions are a newer Lambda type that runs an HTTP server directly. With OAC
they keep the browser's `Authorization` header and need no body hash, which removes both
quirks of Option A.

- Against: Node.js only (our backend is Python); deployed as a .zip only (no container,
  see ADR-0004); no resource in our pinned Terraform provider (6.71.0); billed for memory
  for the whole life of each environment, including idle time.
- Rejected for now. Worth revisiting if Python support and Terraform support arrive.

### Option D: Application Load Balancer → Lambda

- Against: billed by the hour (about 16 USD a month). Practised only in the B11-06 lab.

## Decision

Option A: CloudFront → Lambda function URL with OAC.

Details:

- Function URL auth type `AWS_IAM`. Lambda resource policy allows only
  `cloudfront.amazonaws.com` for this distribution (`aws:SourceArn`), for both
  `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`.
- OAC signing behaviour: always sign.
- CloudFront behaviour `/api/*`: no caching (managed policy `CachingDisabled`); forward
  query strings and the token header; do not forward the viewer `Host` header (managed
  origin request policy `AllViewerExceptHostHeader`), because the function URL expects its
  own host name.
- Frontend API client: adds `x-amz-content-sha256` for every request with a body, using
  the browser's built-in `crypto.subtle.digest("SHA-256", ...)`.

This is checked first in bolt B3 (walking skeleton): a "hello world" POST must work through
CloudFront, and a direct call to the function URL must fail, before any feature depends on
this design.

Fallback: if Option A cannot be made to work in B3, switch to Option B. Only the edge
changes; the FastAPI code stays the same apart from which header carries the token.

## Consequences

- No CORS configuration, because the app and API share one domain.
- The token header choice in ADR-0003 follows from quirk 1.
- The body hash is computed by the browser. It proves the body was not changed between
  CloudFront and Lambda; it is not a security control against the user.
- Requests over 6 MB are impossible; the export (US-60) must stay under that or use S3
  (noted in I-03).
- Rate limiting is not built in. Lambda's concurrency limit, DynamoDB provisioned
  capacity and the budgets act as cost caps. WAF rate rules are tried in the B11 lab.

## What I learned

To be filled in by the owner.
