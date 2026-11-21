# Manual deploy and smoke test

- Tasks: B3-07, B3-08
- Design: `docs/bolts/B3-walking-skeleton.md` (sections 12 to 14); ADR-0004, ADR-0006,
  ADR-0007

## Purpose

Put the app on AWS by hand, and prove that it works and that the side doors are closed.
B6 automates the same steps in GitHub Actions; doing them by hand once first makes the
pipeline easy to follow.

Where the app lives: API Gateway's own address
`https://<id>.execute-api.us-east-1.amazonaws.com` for now, because `satrix.in` is on
hold at the registrar (`use_custom_domain = false`). Once the hold is lifted, "Adding
the domain" below moves it to `https://tethrix.satrix.in`.

## When to use it

- The first deploy: every step, in order.
- Later deploys by hand: steps 3, 4 and 5.

## What gets built

```mermaid
flowchart LR
  user([Browser]) -- "HTTPS" --> apigw[API Gateway<br/>throttling, access logs]
  apigw --> fn[Lambda<br/>FastAPI: API + React app]
  fn --> logs[(CloudWatch Logs)]
  ecr[(ECR)] -. image .-> fn
  ddb[(DynamoDB<br/>not used yet)]
```

## Cost

Cents a month: API Gateway about 1 USD per million requests, ECR a few cents for the
images. Route 53 adds 0.50 USD a month once the domain is on. Nothing is hourly, so
nothing is destroyed at the end of a session; this is the always-on app.

## Prerequisites

- The pull request with the API Gateway change is merged, and you are on an up-to-date
  `main`: `git switch main && git pull`.
- `export AWS_PROFILE=admin` in this terminal (and `aws login` if the session expired).
- Docker Desktop is running.
- Concurrency limit: 10 (checked 2026-11-20), so `lambda_reserved_concurrency` stays -1
  and the account limit is the cap (SR-72).

## Steps

### Step 1: connect Terraform to its state (first time only)

Done on 2026-11-20. For a new laptop:

```sh
cp infra/app/backend.hcl.example infra/app/backend.hcl
# edit infra/app/backend.hcl: replace ACCOUNT_ID (git ignores this file)
terraform -chdir=infra/app init -backend-config=backend.hcl
```

### Step 2: create only the ECR repository (first time only)

Done on 2026-11-20. For the record:

```sh
terraform -chdir=infra/app plan -target=module.ecr -out=tfplan
terraform -chdir=infra/app apply tfplan
```

Why: Lambda cannot be created before its image exists in ECR, and the repository is in
the same stack. `-target` is for exceptions like this one only.

### Step 3: build the app into the image, scan it, push it

```sh
make push-backend
export TF_VAR_backend_image_tag=$(git rev-parse HEAD)
```

Expected: the React files are built, then the backend image (with the React files
inside) is built for arm64, scanned by Trivy with no findings, and pushed. It refuses to
run with uncommitted changes, because the tag is the commit ID.

The `export` line tells Terraform which image to run: Terraform reads any
`TF_VAR_<name>` environment variable as that variable.

### Step 4: create or update everything else

```sh
terraform -chdir=infra/app plan -out=tfplan
terraform -chdir=infra/app apply tfplan
```

Read the plan before applying.

First apply after the switch from CloudFront (2026-11-20): the plan also destroys what
the stopped CloudFront apply had created. Expect to see destroyed: the CloudFront origin
access controls, the CloudFront function, the response headers policy, the frontend
bucket and its settings, and the Lambda function URL (only those that were created).
Expect to see created: the API, its integration, route, stage, access log group, and the
Lambda permission. The Lambda function itself is updated in place (new image) or
created, not replaced. Nothing in `module.ecr` or `module.table` may be destroyed or
replaced; if it is, stop and ask.

First apply of B4 (sign-in): expect created: the Cognito user pool, its domain
(`tethrix-app`), the app client, the JWT authorizer, and the routes `ANY /api/{proxy+}`,
`GET /api/v1/health` and `GET /api/v1/auth/config`. Expect updated in place: the Lambda
function (new image and the three `COGNITO_*` settings) and its role policy (now also
`dynamodb:GetItem` on the table). Nothing destroyed. If the apply says the domain prefix
is taken, add `-var cognito_domain_prefix=tethrix-app-2` (or another free name) and ask
Claude to change the default.

Later deploys: only the Lambda image changes.

### Step 5: smoke and negative tests

```sh
make smoke
terraform -chdir=infra/app output -raw app_url
```

Expected: every line `PASS`, `Failed: 0`. `INFO` lines are notes, not failures: while
the domain is off, the TLS 1.1 check is reported for the record only, and the default
address is the app's address.

The tests are in `scripts/smoke.sh`; each line says what it checks: the page, a script
file and the API with their security headers and caching; the sign-in settings and
Cognito's sign-in page; 401 for API calls without a valid token; Cognito refusing a
foreign callback address; a refused path outside the static folder; and no plain HTTP.
The request body limit (413) is now covered by the unit tests: anonymous POSTs stop at
API Gateway with 401 before the body limit is reached.

Then by hand:

1. Since B4: create your account first (`docs/runbooks/user-accounts.md`,
   `make user-create`). Open the `app_url` address. Expected: Cognito's sign-in page;
   after sign-in (and, the first time, a new password and the authenticator app), the
   dashboard with "API: ok" and your time zone. The first visit after a while takes a
   few seconds (cold start).
2. Developer tools, Console tab: no CSP errors.
3. Logs:

   ```sh
   aws logs tail "$(terraform -chdir=infra/app output -raw lambda_log_group)" --since 15m
   aws logs tail "$(terraform -chdir=infra/app output -raw api_access_log_group)" --since 15m
   ```

   Expected: the app's JSON line per request (request ID, path template, status; no
   bodies, no headers), and API Gateway's line per request (time, IP, method, path,
   status, latency).

### Step 6: check the Lambda role's policy (SR-70)

```sh
role=$(terraform -chdir=infra/app output -raw lambda_role_name)   # productivity-app-api-role
aws iam get-role-policy --role-name "$role" --policy-name "${role%-role}-permissions" \
  --query PolicyDocument --output json > /tmp/lambda-policy.json
aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY \
  --policy-document file:///tmp/lambda-policy.json --query 'findings[].[findingType,issueCode]'
rm /tmp/lambda-policy.json
```

Expected: `[]`. The policy allows writing to the function's own log group and, since
B4, `dynamodb:GetItem` on the app's table (the profile check), nothing else.

### Step 7: confirm Terraform and AWS agree

```sh
terraform -chdir=infra/app plan
```

Expected: `No changes.`

### Step 8: record it

- "Record of deploys" below: date, the first 7 characters of the commit, smoke result.
- Cost Log in the tracker: "B3 first deploy, always-on app, cents a month".
- `make sweep`: the new resources show up, all tagged `Stack = app`.

Never paste Terraform outputs into docs: the ECR and execute-api addresses identify the
account.

## Adding the domain

Design: `docs/bolts/domain-switch.md` (approved 2026-11-21). Done once. Cost: the Route
53 zone, 0.50 USD a month.

Before you start: `dig +short NS satrix.in` shows the two `domaincontrol.com` names (the
parent is not on hold), and `use_custom_domain` defaults to `true` on `main`.

1. Create only the zone, and read its four name servers:

   ```sh
   terraform -chdir=infra/app plan -target='aws_route53_zone.app[0]' -out=tfplan
   terraform -chdir=infra/app apply tfplan
   terraform -chdir=infra/app output name_servers
   ```

   Terraform warns that `-target` is for exceptional cases; this is one.

2. At GoDaddy, `satrix.in`, the DNS records page: add four records, type `NS`, name
   `tethrix`, one per name server from step 1 (without the dot at the end if GoDaddy
   refuses it), TTL 1 hour. Do not touch the separate "Nameservers" setting: that would
   hand the whole of `satrix.in` away.

3. Wait until the delegation answers (minutes, sometimes up to an hour):

   ```sh
   dig +short NS tethrix.satrix.in @1.1.1.1
   ```

   Expected: the four `awsdns` names from step 1.

4. Everything else, with the default address still on:

   ```sh
   terraform -chdir=infra/app plan -var disable_default_endpoint=false -out=tfplan
   terraform -chdir=infra/app apply tfplan
   ```

   Expected in the plan: created: the CAA record, the certificate, its validation
   record and validation, the API's custom domain, the mapping, the A and AAAA
   records. Updated in place: the Cognito app client (callback and sign-out URLs).
   Nothing destroyed. The certificate step waits until ACM has seen the record, usually
   a few minutes.

5. Check the domain:

   ```sh
   ALLOW_DEFAULT_ENDPOINT=1 make smoke
   ```

   Expected: `Failed: 0`, and one INFO line saying the default address still answers.
   Then open `https://tethrix.satrix.in`, sign in (once more: the old address's
   session does not carry over) and check the dashboard.

6. Switch off the default address:

   ```sh
   terraform -chdir=infra/app plan -out=tfplan
   terraform -chdir=infra/app apply tfplan
   ```

   Expected: one change, the API updated in place (`disable_execute_api_endpoint`).

7. `make smoke`. Expected: `Failed: 0`, with "default execute-api address is switched
   off" and "TLS 1.1 is refused" as PASS lines.

8. Record it below and in the Cost Log ("Route 53 zone, 0.50 USD a month from now on").

Rollback (the name stops working, for example if the hold comes back): one apply with
`-var use_custom_domain=false`. The execute-api address comes back and Cognito's URLs
follow it. Remove the NS records at GoDaddy before or right after (T-032).

## Removing the domain

Order matters (T-032, subdomain takeover): if the zone is deleted while GoDaddy still
points `tethrix` at it, someone else could create a zone with the same name servers and
take the name.

1. At GoDaddy, delete the four `NS` records named `tethrix`.
2. Wait an hour (the TTL), so caches forget them.
3. Then apply with `-var use_custom_domain=false`, or destroy everything (Undo).

## Problems

| Problem | What to do |
|---|---|
| `Error: No image yet` | `TF_VAR_backend_image_tag` is not set in this terminal. Run the `export` from step 3 |
| `make push-backend` says the tag already exists | Tags are immutable: the image for this commit is already in ECR. Skip the push, use the same tag |
| Lambda says the image manifest or media type is not supported | Check that `--provenance=false --sbom=false` are in the build line; note it below and ask Claude |
| The page answers 500 or `Internal Server Error` | `aws logs tail` on the Lambda log group (step 5). `STATIC_DIR ... index.html does not exist` means the image was built without the React files: use `make push-backend`, not a plain `docker build` |
| `{"message":"Internal Server Error"}` (API Gateway's own wording) | API Gateway could not call Lambda: check the access log's `integrationErr` field, then the Lambda permission in the plan |
| `{"message":"Too Many Requests"}` | Throttling (10 a second, bursts of 20) did its job. Wait a moment |
| The certificate waits a long time, then fails (domain step 4) | The NS records are missing or not visible yet. Check with `dig`, then apply again |

## Undo

Not part of a normal session: the app is always on. To take everything down:

1. With the domain: remove the four NS records for `tethrix` at GoDaddy first and
   wait an hour ("Removing the domain", T-032).
2. `terraform -chdir=infra/app apply -var final_destroy=true` (turns off deletion
   protection), then `terraform -chdir=infra/app destroy`.

## Record of deploys

| Date | Commit | Smoke result | Notes |
|---|---|---|---|
| 2026-11-21 | 899c7cd | Passed twice, 0 failed | Domain switch: zone, NS records at GoDaddy, first apply with the default address on (`ALLOW_DEFAULT_ENDPOINT=1 make smoke`), second apply turned it off (`make smoke`). Sign-in on `tethrix.satrix.in` works |
| 2026-11-20 | e8a2622 | Passed, 0 failed | B4 sign-in: Cognito pool, authorizer, routes. First user created; sign-in with authenticator app works. Owner: "authentication worked as expected" |
| 2026-11-20 | 97e3d10 | 17 passed, 0 failed | First deploy on API Gateway, on the default execute-api address. Owner: "works as expected" |
| 2026-11-20 | e1c08a7 | Not reached | First apply stopped at the CloudFront distribution (account needs a payment method and the Paid plan for CloudFront). Switched to API Gateway (ADR-0007) |

Free plan check:

| Service | How it was confirmed | Result |
|---|---|---|
| CloudFront | Apply refused; AWS Support: needs a payment method and the Paid plan for this account | Not available to us (ADR-0007) |
| Cognito (Lite) | Applied 2026-11-20 without errors; AWS docs list Cognito in the Free Tier (10,000 monthly users on Lite) | Works on the Free plan |
| API Gateway, Route 53, ACM, Lambda, ECR, DynamoDB, CloudWatch | AWS docs, "Supported AWS services for Sign up for AWS (new)", checked 2026-11-20 | Listed as Free Tier services |
