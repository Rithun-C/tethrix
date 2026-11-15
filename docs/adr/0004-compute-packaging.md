# ADR-0004: Compute packaging (how the backend is built and run)

- Status: Accepted 2026-11-15
- Date: 2026-11-15
- Task: I-07

## Context

FastAPI is a normal Python web app: it expects a web server (uvicorn) to hand it HTTP
requests. Lambda instead hands the function an "event" (a JSON description of the
request). Something has to translate between the two, and the code has to be packaged
for Lambda.

Goals: learn containers properly (a project goal), run the same thing locally and in AWS,
and keep cost close to zero.

Words used below:

- Container image: a packaged file system with the app, its libraries and the Python
  runtime, built from a Dockerfile.
- ECR (Elastic Container Registry): AWS's private store for container images.
- Lambda Web Adapter: a small open-source program from AWS that runs next to the app
  inside Lambda. It turns Lambda events back into normal HTTP requests, so the app runs
  unchanged with uvicorn.
- Mangum: a Python library that does the same translation inside the app code.
- Cold start: the delay when Lambda starts a new copy of the function after idle time.

## Options

### Option A: Container image in ECR, with Lambda Web Adapter

- For: the exact same image runs in Docker Compose on the laptop and in Lambda; FastAPI
  runs with uvicorn as it normally would, with no Lambda-specific code; real container
  practice (Dockerfile, multi-stage builds, image scanning with Trivy, a private
  registry); the image can also run on ECS for the B11-06 lab without changes.
- Against: ECR storage costs about 0.10 USD per GB a month (a few cents for our images);
  cold starts can be slightly slower than a small zip; deploys push a few hundred MB.

### Option B: Zip package with Mangum

- For: simplest and smallest; no registry; fast deploys.
- Against: Lambda-specific code in the app; local runs differ from AWS; no container
  practice for the backend.

### Option C: Zip package with Lambda Web Adapter as a layer

- For: no Lambda-specific code, no registry.
- Against: still not a container, so local and AWS differ; layers add their own
  versioning to manage.

## Decision

Option A: container image in ECR, with Lambda Web Adapter.

Details:

| Setting | Value | Why |
|---|---|---|
| CPU architecture | arm64 (Graviton) | About 20% cheaper per second than x86, and Apple Silicon Macs build it natively |
| Base image | Official slim Python image, pinned by digest (chosen in B2) | Small, well maintained |
| Web Adapter | Copied in from AWS's public image, pinned by version and digest (checked in B3) | Pinned like every other dependency |
| User inside the container | Non-root | If the app is compromised, the attacker is not root inside the container |
| Memory, timeout | 512 MB, 10 seconds (tuned in B3) | Enough for FastAPI; a short timeout stops runaway requests |
| ECR repository | Private, scan on push, immutable tags, keep only the last 5 images | Scanning is free; immutable tags mean a tag always means the same image; the lifecycle rule keeps storage cost tiny |
| Image tags | The Git commit ID | Every running image can be traced to its exact code |

## Consequences

- B2 writes the Dockerfile (multi-stage, non-root, pinned digests) and runs it in Docker
  Compose.
- B3 creates the ECR repository and the Lambda function from the image.
- Trivy scans every image before it is pushed (in CI from B6).
- Cold starts of 1 to 3 seconds after idle are expected and accepted (I-01 quality goals).
- ECR storage is the one small recurring cost of the backend.

## What I learned

To be filled in by the owner.
