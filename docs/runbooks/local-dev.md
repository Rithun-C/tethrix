# Local development

- Tasks: B2-01, B2-03, B2-04, B2-05, B2-06
- Design: `docs/bolts/B2-local-dev.md`

## Purpose

Run the app on the laptop with Docker Compose, and run its checks. Nothing here touches
AWS and nothing costs money.

## When to use it

Every time you work on the app.

## Prerequisites

- Docker Desktop is running.
- You are in the repo folder.

## What runs

```mermaid
flowchart LR
  you([You<br/>curl or browser]) -- "127.0.0.1:8080" --> backend[backend<br/>FastAPI, hot reload]
  backend --> ddb[(dynamodb<br/>DynamoDB Local<br/>in memory)]
  init[db-init<br/>runs once, then exits] -- "creates table,<br/>writes seed data" --> ddb
  backend -. "starts after" .-> init
```

| Container | What it is | Address on the laptop |
|---|---|---|
| `backend` | Our FastAPI app, restarting itself when a file in `app/backend/src` changes | http://localhost:8080 |
| `dynamodb` | DynamoDB Local | http://localhost:8000 |
| `db-init` | Creates the table and the seed data, then stops | none |

The frontend joins in pull request 2.

## Start, look, stop

1. Start: `make up`. It builds the image first; the first build downloads the packages.
2. Check it answers:

   ```sh
   curl -i http://localhost:8080/api/v1/health
   ```

   Expected: `HTTP/1.1 200 OK`, a header `x-request-id`, and `{"status":"ok"}`.
3. See the log line that request wrote: `make logs` (Ctrl-C stops watching, not the
   app). Each line is one JSON object. Find the one with `"message": "request"`.
4. See what is running: `make ps`.
5. Stop: `make down`.

## The local database

It lives in memory. `make down` or `make reset-db` empties it, and the next start loads
the seed data again: two made-up users, Alice and Bob, each with a profile and a few
todos.

To look inside, use the AWS CLI against the local address. The profile is not used; the
fake key only stops the CLI from complaining:

```sh
AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \
aws dynamodb scan --table-name productivity-app-data \
  --endpoint-url http://localhost:8000 --region us-east-1 \
  --query 'Items[].[PK.S, SK.S, title.S]' --output table
```

Always pass `--endpoint-url` here. Without it the command goes to real AWS.

## Checks

| Command | What it does |
|---|---|
| `make lint-backend` | ruff (format and lint) and mypy |
| `make test-backend` | pytest, including the tests against DynamoDB Local |
| `make audit-backend` | pip-audit on the locked packages |
| `make hadolint` | Dockerfile lint |
| `make image-scan` | Builds the image that ships and scans it with Trivy |
| `make check` | All of the above plus the B1 scanners: the same as CI |
| `make fmt-backend` | Formats the code and applies safe lint fixes |

## Adding or updating a Python package

1. Go through the checklist in `docs/dependency-policy.md`, section 2.
2. Add it to `app/backend/pyproject.toml` with an exact version (`name==1.2.3`).
3. `make lock` rewrites `uv.lock`.
4. `make up` rebuilds the image with the new package.
5. `make check`, then commit `pyproject.toml` and `uv.lock` together.

`exclude-newer = "7 days"` in `pyproject.toml` stops uv from choosing anything published
in the last week, so a version newer than that cannot be locked yet.

## Problems

| Problem | What to do |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop |
| `port is already allocated` | Something else uses 8080 or 8000. `make down`, or find it with `lsof -i :8080` |
| The image build hangs on a `Downloading ...` line | Seen on 2026-11-15: this network's IPv4 route to PyPI's file server is very slow (0.5 MB in 40 seconds, against 15 MB in 5 seconds over IPv6), and Docker's default network has no IPv6. Fix: a file `local.mk` in the repo folder with the line `BUILD_NETWORK := host`. Builds then use the host network, which has IPv6. Git ignores `local.mk`, so the setting stays on this laptop. If `make lock` stalls the same way, run `cd app/backend && uv lock` on the laptop instead |
| `make audit-backend` fails with `Read timed out` | The same network problem, while pip-audit asks PyPI about vulnerabilities. Run it again |
| DynamoDB Local answers 500 and its log says `failed to map segment` | Its `/tmp` must allow running code. `compose.yaml` sets `tmpfs: /tmp:exec` for it; do not remove that |
| A code change does not show | `make logs` and look for a reload line or a Python error |
| `uv sync` fails with "lockfile needs to be updated" | `pyproject.toml` was changed without `make lock` |

## Undo

`make down` removes the containers. To also remove the built images:
`docker image rm productivity-app-backend:dev productivity-app-backend:runtime`.
