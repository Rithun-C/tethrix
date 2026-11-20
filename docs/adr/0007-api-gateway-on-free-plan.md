# ADR-0007: API Gateway in front of Lambda, frontend served by the backend

- Status: Accepted 2026-11-20
- Date: 2026-11-20
- Task: B3-04, B3-05
- Supersedes: ADR-0002 (CloudFront to Lambda function URL with OAC)

## Context

The first deploy of B3 failed at the CloudFront distribution: "Your account must be
verified before you can add new CloudFront resources." AWS Support then answered that
CloudFront cannot be enabled for this account until it has a payment method and is on
the Paid plan.

Hard constraint 1 is "AWS Free plan only". The owner decided on 2026-11-20 to stay on the
Free plan. CloudFront is therefore unavailable, and by the project's rule it becomes
theory (B3-09).

What we still need:

- HTTPS for the page and the API, from B4 on with a sign-in token in every request.
- One address for the page and the API, so no CORS is needed.
- The custom domain `tethrix.satrix.in` when the registrar lifts its hold (ADR-0006).
- Cost close to zero, nothing hourly.

Words used below:

- API Gateway HTTP API: AWS's managed front door for HTTP requests. It receives each
  request on HTTPS and hands it to a Lambda function. Billed per request.
- Route `$default`: the catch-all route of an HTTP API; every request that matches no
  other route goes there.
- Stage: a named, deployed version of the API. We use the one stage `$default`, which
  gives addresses without a stage name in the path.
- Execute-api endpoint: the address every API gets by default,
  `https://<id>.execute-api.us-east-1.amazonaws.com`.
- Regional custom domain: our own name on API Gateway, with an ACM certificate in the
  same region.
- Throttling: API Gateway refuses requests above a set rate with 429, before Lambda runs.

## Options

### Option A: Paid plan, keep CloudFront (ADR-0002)

- Against: breaks hard constraint 1. The account would no longer just close when the
  credits or the plan run out; anything beyond the credits would be billed to the card.
  Rejected by the owner.

### Option B: API Gateway HTTP API in front of Lambda; FastAPI also serves the React files

Every request, page or API, goes to API Gateway, which calls the Lambda function.
FastAPI answers `/api/*` as before, and also serves the built React files: `/assets/*`
as files and every other path with `index.html`.

- For: HTTPS with TLS 1.2 on our own domain; built-in throttling; access logs; no OAC,
  so the normal `Authorization` header works and no body hash is needed; one address,
  no CORS; the Lambda needs no public URL at all; already the planned fallback in
  ADR-0002.
- Against: no CDN, so every page load runs Lambda (about three requests: page, script,
  styles), and the first visit after idle waits for a cold start; security headers
  move from CloudFront into the app; API Gateway costs about 1 USD per million
  requests.
- Cost: cents a month.

### Option C: Frontend on S3 website hosting, API on API Gateway

- Against: S3 website addresses are HTTP only and need a public bucket. Signing in over
  HTTP is not acceptable. Rejected.

### Option D: Amplify Hosting for the frontend

- Against: Amplify Hosting serves through CloudFront, so it is likely blocked the same
  way; and it adds a second address (CORS). Rejected.

### Option E: Lambda function URL with auth "none" for everything

- Against: no custom domain, no throttling, a random public address. Kept only as the
  route if API Gateway also turns out to be unavailable on the Free plan.

## Decision

Option B. Approved by the owner on 2026-11-20 with the recommendations (B3 decisions 9
to 11), as the way forward "for now": CloudFront may come back later (see the last
section).

Free plan check: AWS's page "Supported AWS services for Sign up for AWS (new)" (read
2026-11-20) lists API Gateway, Route 53, ACM, Lambda, ECR, DynamoDB and CloudWatch Logs
as Free Tier services, with no restriction that affects us. The same page also lists
CloudFront, so the CloudFront block is about this account (verification, payment
method), not the Free plan as such. AWS Support's answer for our account stands until
they say otherwise.

| Setting | Value | Why |
|---|---|---|
| API type | HTTP API (not REST API) | Cheaper and simpler; all we need |
| Routes | One catch-all `$default` route to Lambda | FastAPI decides what each path means |
| Integration | Lambda proxy, payload format 2.0 | The Web Adapter understands it |
| Stage | `$default`, auto-deploy | Addresses without a stage name |
| Throttling | 10 requests a second, bursts of 20 | Caps a flood before it reaches Lambda (T-021) |
| Access logs | JSON lines to a log group with 14 days retention (SR-43) | One line per request at the edge, like CloudFront logs would have been |
| Lambda | No function URL any more; a permission lets only this API invoke it | Nothing else can reach the function (SR-62) |
| Domain | Regional custom domain `tethrix.satrix.in`, ACM certificate, security policy TLS 1.2, Route 53 `A` and `AAAA` alias records | ADR-0006, SR-50 |
| Default endpoint | On while the domain is off; turned off when the domain is on | With the domain, the only way in is our name |
| Security headers | Set by FastAPI middleware on every response (CSP, HSTS, nosniff, Referrer-Policy, X-Frame-Options) | Replaces the CloudFront headers policy (SR-60, SR-61) |
| Static files | Built React files copied into the backend image, served by FastAPI; `/assets/*` cached for a year, `index.html` never | Same caching rules as the S3 design |

## Consequences

- ADR-0002 is superseded. The OAC quirks are gone: the browser no longer sends
  `x-amz-content-sha256`, and the frontend's hash code is removed.
- ADR-0003 chose the `X-Auth-Token` header only because OAC overwrote `Authorization`.
  B4 revisits this: the standard `Authorization: Bearer` header works again.
- The backend image now contains the frontend build. The image build needs the
  frontend's `dist` files first (a `make` target does both).
- CloudFront, OAC, SigV4 signing by CloudFront and CloudFront Functions become theory
  in B3-09.
- The resources already created for CloudFront (origin access controls, the routing
  function, the headers policy, the frontend bucket, the function URL) are removed by
  the next apply. The Lambda function, ECR, the image and the table stay.
- Every page load uses Lambda. At our size this stays far inside the free tier; a
  cold start of 1 to 3 seconds on the first visit after idle is accepted (ADR-0004).

## Switching back to CloudFront later

If AWS enables CloudFront for this account while it stays on the Free plan (for example
after a payment method is verified, without upgrading), the CloudFront design can
return. It is in Git history: pull requests #12 (`cloudfront.tf`, `frontend.tf`,
`functions/spa_router.js`) and #13 (default-domain switch). The path back would be:

1. New ADR that supersedes this one.
2. CloudFront in front of API Gateway (simplest: API Gateway becomes CloudFront's
   origin, no OAC needed), or back to the function URL with OAC (ADR-0002, with its
   body-hash and header quirks).
3. Static files can stay in the image or move back to S3.

Never upgrade to the Paid plan for this: hard constraint 1, and the upgrade cannot be
undone.

## What I learned

To be filled in by the owner.
