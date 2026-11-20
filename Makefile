# Shortcuts for the checks every change must pass. `make help` lists them.
# CI runs these same targets, so a pass here means a pass there.
#
# The scanners run as Docker images pinned in tools/versions.env. Docker Desktop must be
# running. Terraform itself runs from the laptop install.
#
# The app's own tests and linters run inside its dev container (see compose.yaml), so
# the laptop and CI use the same Python and the same package versions.

include tools/versions.env

SHELL := /bin/bash
ROOT  := $(CURDIR)

# Every Terraform root (a folder you can run `terraform plan` in). Add new ones here.
TF_STACKS := infra/bootstrap infra/app infra/labs/_template

# Providers are downloaded once and shared between the stacks.
export TF_PLUGIN_CACHE_DIR ?= $(HOME)/.terraform.d/plugin-cache
$(shell mkdir -p "$(TF_PLUGIN_CACHE_DIR)")

# Mounts the repo into the container at /src. Tool caches go in .cache/ (git ignores it).
DOCKER_RUN := docker run --rm -v "$(ROOT)":/src -w /src

COMPOSE := docker compose

# Which network image builds use to download packages. "default" is Docker's own
# network, which has no IPv6. "host" lets a build use IPv6; needed on networks where
# IPv4 downloads from PyPI stall. Set it once for this laptop in local.mk (git ignores
# it):   BUILD_NETWORK := host
-include local.mk
BUILD_NETWORK ?= default
DOCKER_BUILD  := docker build --network=$(BUILD_NETWORK)
# The same choice for one-off containers that need the internet (the audits and the
# lock commands). `docker run` calls the default network "bridge".
NET_RUN       := docker run --rm --network=$(BUILD_NETWORK:default=bridge)
# Runs a command in the backend dev container. --no-deps: without starting the database.
BACKEND      := $(COMPOSE) run --rm --no-deps backend
BACKEND_DB   := $(COMPOSE) run --rm backend
# The same container, but with the backend folder writable (for formatting and locking).
BACKEND_RW   := docker run --rm -v "$(ROOT)/app/backend":/app -e RUFF_CACHE_DIR=/tmp/ruff
# The same idea for the frontend dev container.
FRONTEND     := $(COMPOSE) run --rm --no-deps frontend
NODE_IMAGE    = $(shell sed -n 's/^FROM \(node:[^ ]*\) AS node-base/\1/p' app/frontend/Dockerfile)

.DEFAULT_GOAL := help
.PHONY: help fmt fmt-check validate lint gitleaks gitleaks-staged checkov semgrep \
        semgrep-test trivy scan check hooks sweep up down logs ps reset-db seed openapi \
        guard-local-auth build lock fmt-backend lint-backend test-backend audit-backend hadolint \
        image-build image-scan check-backend check-images build-backend build-frontend \
        lock-frontend fmt-frontend lint-frontend test-frontend audit-frontend check-frontend \
        push-backend smoke frontend-dist user-create user-disable user-delete

help: ## List the commands
	@grep -hE '^[a-z-]+:.*## ' Makefile | awk -F ':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

fmt: ## Format all Terraform files
	terraform fmt -recursive infra

fmt-check: ## Fail if any Terraform file is not formatted
	terraform fmt -check -diff -recursive infra

# Validate checks the code only. It must not need AWS credentials or touch real state:
# - -backend=false downloads providers without contacting the state bucket.
# - TF_DATA_DIR points Terraform at a scratch folder in .cache/ instead of the stack's
#   own .terraform folder, so a stack you have already initialised is left alone.
validate: ## terraform validate on every stack, without a backend
	@set -e; for d in $(TF_STACKS); do \
	  echo "== validate $$d"; \
	  export TF_DATA_DIR="$(ROOT)/.cache/terraform/$$d"; \
	  terraform -chdir=$$d init -backend=false -input=false >/dev/null; \
	  terraform -chdir=$$d validate; \
	done

# Guard 2 of the local sign-in (B4-05, SR-06): Terraform must never set the local-only
# settings, so a deployed function always checks Cognito tokens. The app also refuses to
# start in Lambda with them (guard 1); this catches the mistake before a deploy.
guard-local-auth: ## Fail if any Terraform file sets a local-only sign-in setting
	@# Comment lines (starting with #) are skipped: they cannot set anything.
	@if grep -rnE 'AUTH_MODE|LOCAL_OIDC_|DYNAMODB_ENDPOINT_URL' --include='*.tf' infra | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#'; then \
	  echo "Local-only settings found in Terraform (see above)."; exit 1; \
	else echo "guard-local-auth: no local-only settings in Terraform"; fi

lint: guard-local-auth ## tflint on every stack (and the local sign-in guard)
	@mkdir -p .cache/tflint
	$(DOCKER_RUN) -e GITHUB_TOKEN -e TFLINT_PLUGIN_DIR=/src/.cache/tflint \
	  --entrypoint /bin/sh $(TFLINT_IMAGE) -c '\
	    set -e; tflint --init --config /src/.tflint.hcl; \
	    for d in $(TF_STACKS); do echo "== tflint $$d"; \
	      tflint --chdir $$d --config /src/.tflint.hcl; done'

# Scans every commit in the history. It reads git, so files that git ignores (such as
# backend.hcl, which holds the account ID) are correctly left out.
gitleaks: ## Look for secrets and the account ID in the whole git history
	@if [ ! -d .git ]; then echo "No git repo yet. Stage files, then: make gitleaks-staged"; exit 1; fi
	$(DOCKER_RUN) $(GITLEAKS_IMAGE) git --redact --no-banner --verbose .

gitleaks-staged: ## Look for secrets in staged changes (used by pre-commit)
	@$(DOCKER_RUN) $(GITLEAKS_IMAGE) git --pre-commit --staged --redact --no-banner --verbose .

checkov: ## Terraform and workflow security settings
	$(DOCKER_RUN) $(CHECKOV_IMAGE) -d /src --framework terraform github_actions dockerfile kubernetes \
	  --skip-path '\.terraform' --skip-path '\.cache' --quiet --compact

semgrep-test: ## Prove our own Semgrep rules catch what they should
	$(DOCKER_RUN) $(SEMGREP_IMAGE) semgrep --test --config .semgrep/rules .semgrep/tests

semgrep: semgrep-test ## Insecure code patterns: the public rules plus our own
	$(DOCKER_RUN) $(SEMGREP_IMAGE) semgrep scan --config p/default --config .semgrep/rules \
	  --error --metrics=off --quiet .

trivy: ## Vulnerable dependencies, misconfigurations and secrets
	@mkdir -p .cache/trivy
	$(DOCKER_RUN) -e TRIVY_CACHE_DIR=/src/.cache/trivy $(TRIVY_IMAGE) fs \
	  --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --exit-code 1 \
	  --skip-dirs '**/.terraform' --skip-dirs .cache --skip-dirs .semgrep/tests \
	  --skip-files '**/tfplan' --ignorefile /src/.trivyignore.yaml .

scan: gitleaks checkov semgrep trivy ## All four security scanners

# ---- Local app (Docker Compose) -------------------------------------------------

up: build ## Start the app on the laptop: open http://localhost:5173
	$(COMPOSE) up --detach --wait frontend
	@echo "App:     http://localhost:5173"
	@echo "Backend: http://localhost:8080/api/v1/health"

down: ## Stop the app and remove its containers
	$(COMPOSE) down --remove-orphans

logs: ## Follow the logs of all containers (Ctrl-C to stop watching)
	$(COMPOSE) logs --follow

ps: ## Show which containers are running
	$(COMPOSE) ps

# The local database lives in memory, so restarting it empties it. db-init then
# creates the table and the seed data again.
reset-db: ## Empty the local database and load the seed data again
	$(COMPOSE) rm --stop --force dynamodb db-init
	$(COMPOSE) up --detach --wait frontend

seed: ## Write the seed data again (same keys, so nothing is duplicated)
	$(BACKEND_DB) python scripts/seed.py

openapi: ## Write the API description to .cache/openapi.json
	@mkdir -p .cache
	$(BACKEND) python scripts/export_openapi.py > .cache/openapi.json
	@echo "Written: .cache/openapi.json"

# Built with plain `docker build`, not `docker compose build`: Compose then finds the
# image by its name. (Compose's own build ignored the network setting when tested.)
build: build-backend build-frontend ## Build both dev images

build-backend:
	$(DOCKER_BUILD) --quiet --target dev --tag productivity-app-backend:dev app/backend

build-frontend:
	$(DOCKER_BUILD) --quiet --target dev --tag productivity-app-frontend:dev app/frontend

# ---- Backend checks -----------------------------------------------------------------

lock: ## Recreate app/backend/uv.lock after changing pyproject.toml
	$(DOCKER_BUILD) --quiet --target base --tag productivity-app-backend:base app/backend
	$(NET_RUN) -v "$(ROOT)/app/backend":/app productivity-app-backend:base uv lock

fmt-backend: build-backend ## Format the backend code and apply safe lint fixes
	$(BACKEND_RW) productivity-app-backend:dev sh -c "ruff format . && ruff check --fix ."

lint-backend: build-backend ## ruff (format and lint) and mypy
	$(BACKEND) sh -c "ruff format --check . && ruff check . && mypy"

test-backend: build-backend ## pytest, including the tests that use DynamoDB Local
	$(BACKEND_DB) pytest

# pip-audit only reads a list of packages; it installs nothing. `uv export` writes that
# list from uv.lock, with hashes. Development tools are included: they run on the
# laptop and in CI, so a vulnerable one matters too.
audit-backend: build-backend ## Known vulnerabilities in the Python packages
	$(NET_RUN) --read-only --tmpfs /tmp -e UV_CACHE_DIR=/tmp/uv \
	  -v "$(ROOT)/app/backend/pyproject.toml":/app/pyproject.toml:ro \
	  -v "$(ROOT)/app/backend/uv.lock":/app/uv.lock:ro \
	  productivity-app-backend:dev sh -c "uv export --quiet --locked --format requirements-txt --output-file /tmp/requirements.txt \
	  && pip-audit --requirement /tmp/requirements.txt --require-hashes --disable-pip --timeout 60"

# ---- Frontend checks ----------------------------------------------------------------

# Run after changing package.json. It only rewrites package-lock.json; nothing is
# installed on the laptop. The image is rebuilt from the lockfile by `make up`.
lock-frontend: ## Recreate app/frontend/package-lock.json after changing package.json
	$(NET_RUN) -v "$(ROOT)/app/frontend":/app -w /app \
	  -e NPM_CONFIG_CACHE=/tmp/npm $(NODE_IMAGE) npm install --package-lock-only

fmt-frontend: build-frontend ## Format the frontend code
	docker run --rm -v "$(ROOT)/app/frontend":/work -w /work -e NODE_PATH=/app/node_modules \
	  productivity-app-frontend:dev prettier --write .

lint-frontend: build-frontend ## Prettier check, ESLint and the TypeScript type check
	$(FRONTEND) sh -c "prettier --check . && eslint . && tsc --noEmit"

test-frontend: build-frontend ## Vitest
	$(FRONTEND) vitest run --configLoader runner

# Fails on High or Critical (SR-82). Lower ones are printed and logged in the
# findings log.
audit-frontend: build-frontend ## Known vulnerabilities in the npm packages
	$(NET_RUN) --read-only --tmpfs /tmp \
	  -v "$(ROOT)/app/frontend/package.json":/app/package.json:ro \
	  -v "$(ROOT)/app/frontend/package-lock.json":/app/package-lock.json:ro \
	  -v "$(ROOT)/app/frontend/.npmrc":/app/.npmrc:ro \
	  productivity-app-frontend:dev npm audit --audit-level=high

check-frontend: lint-frontend test-frontend audit-frontend ## All frontend checks

# ---- Images -------------------------------------------------------------------------

hadolint: ## Lint the Dockerfiles
	$(DOCKER_RUN) $(HADOLINT_IMAGE) hadolint app/backend/Dockerfile app/frontend/Dockerfile

# Building the frontend "static" image also runs the production build (tsc + vite build).
# The React build output, copied out of the frontend image's `dist` stage. The backend
# runtime image includes it (ADR-0007).
frontend-dist: ## Build the React files into .cache/frontend-dist
	@rm -rf .cache/frontend-dist
	$(DOCKER_BUILD) --quiet --target dist --output type=local,dest=.cache/frontend-dist app/frontend

image-build: frontend-dist ## Build the images that ship: backend runtime (with the React app) and frontend static
	$(DOCKER_BUILD) --quiet --build-context frontend-dist=.cache/frontend-dist \
	  --target runtime --tag productivity-app-backend:runtime app/backend
	$(DOCKER_BUILD) --quiet --target static --tag productivity-app-frontend:static app/frontend

# The image is saved to a file and Trivy scans the file. The other way, giving the Trivy
# container the Docker socket, would hand it control over Docker on this machine.
# --ignore-unfixed: a vulnerability with no fix yet is reported by nobody's action but
# time; the weekly base image update picks the fix up when it exists.
image-scan: image-build ## Scan the shipped images for vulnerabilities and secrets
	@mkdir -p .cache/images .cache/trivy
	@set -e; for image in backend:runtime frontend:static; do \
	  name=$${image%%:*}; echo "== trivy image $$image"; \
	  docker save --output .cache/images/$$name.tar productivity-app-$$image; \
	  $(DOCKER_RUN) -e TRIVY_CACHE_DIR=/src/.cache/trivy $(TRIVY_IMAGE) image \
	    --input /src/.cache/images/$$name.tar --scanners vuln,secret \
	    --severity HIGH,CRITICAL --ignore-unfixed --ignorefile /src/.trivyignore.yaml \
	    --exit-code 1 --quiet; \
	done

check-backend: lint-backend test-backend audit-backend ## All backend checks

check-images: hadolint image-scan ## All image checks

check: fmt-check validate lint scan check-backend check-frontend check-images ## Everything CI runs
	@echo "All checks passed."

hooks: ## Install the pre-commit hooks (once per clone)
	uv tool install pre-commit==$(PRE_COMMIT_VERSION)
	pre-commit install

sweep: ## Read-only check for running AWS resources
	./scripts/sweep.sh

# ---- Deploy: run by the owner only -------------------------------------------------------
# These need AWS credentials (export AWS_PROFILE=admin first), which Claude does not have.
# Each step is explained in docs/runbooks/deploy-manual.md. B6 runs the same steps in CI.
TF_APP     := terraform -chdir=infra/app
AWS_REGION := us-east-1

# The tag is the commit ID (ADR-0004), so the image must be built from exactly that commit:
# uncommitted changes would be in the image but not in Git. The image is scanned as the
# exact file that is pushed. --provenance=false --sbom=false: Lambda does not accept the
# extra attestation entries Docker adds by default.
push-backend: ## (owner, AWS) Build the React app into the backend image, scan it, push it to ECR
	@test -z "$$(git status --porcelain)" || { echo "Commit or stash your changes first: the image tag is the commit ID."; exit 1; }
	@$(MAKE) --no-print-directory frontend-dist
	@set -e; \
	repo=$$($(TF_APP) output -raw ecr_repository_url); \
	registry=$${repo%%/*}; \
	tag=$$(git rev-parse HEAD); \
	echo "== build backend image for commit $$tag"; \
	$(DOCKER_BUILD) --quiet --platform linux/arm64 --provenance=false --sbom=false \
	  --build-context frontend-dist=.cache/frontend-dist \
	  --target runtime --tag "$$repo:$$tag" app/backend; \
	echo "== trivy: the exact image that will be pushed"; \
	mkdir -p .cache/images .cache/trivy; \
	docker save --output .cache/images/push.tar "$$repo:$$tag"; \
	$(DOCKER_RUN) -e TRIVY_CACHE_DIR=/src/.cache/trivy $(TRIVY_IMAGE) image \
	  --input /src/.cache/images/push.tar --scanners vuln,secret \
	  --severity HIGH,CRITICAL --ignore-unfixed --ignorefile /src/.trivyignore.yaml \
	  --exit-code 1 --quiet; \
	echo "== push"; \
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin "$$registry" >/dev/null; \
	docker push --quiet "$$repo:$$tag"; \
	docker logout "$$registry" >/dev/null; \
	echo; echo "Pushed. Next step: $(TF_APP) apply -var backend_image_tag=$$tag"

# User accounts (B4-08). The owner runs these with their AWS profile; see
# docs/runbooks/user-accounts.md. EMAIL is typed on the command line, never stored.
USER_ARGS = "$$($(TF_APP) output -raw cognito_user_pool_id)" "$$($(TF_APP) output -raw table_name)"

user-create: ## (owner, AWS) Create a user: make user-create EMAIL=... TZ=Asia/Kolkata
	@test -n "$(EMAIL)" -a -n "$(TZ)" || { echo "Usage: make user-create EMAIL=you@example.com TZ=Asia/Kolkata"; exit 1; }
	@./scripts/user.sh create $(USER_ARGS) "$(EMAIL)" "$(TZ)"

user-disable: ## (owner, AWS) Disable a user and sign them out: make user-disable EMAIL=...
	@test -n "$(EMAIL)" || { echo "Usage: make user-disable EMAIL=you@example.com"; exit 1; }
	@./scripts/user.sh disable $(USER_ARGS) "$(EMAIL)"

user-delete: ## (owner, AWS) Delete a user and their profile: make user-delete EMAIL=...
	@test -n "$(EMAIL)" || { echo "Usage: make user-delete EMAIL=you@example.com"; exit 1; }
	@./scripts/user.sh delete $(USER_ARGS) "$(EMAIL)"

smoke: ## (owner, AWS) Smoke and negative tests against the deployed app
	@./scripts/smoke.sh "$$($(TF_APP) output -raw app_url | sed 's|https://||')" \
	  "$$($(TF_APP) output -raw api_endpoint | sed 's|https://||')"
