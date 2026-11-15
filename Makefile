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
# Runs a command in the backend dev container. --no-deps: without starting the database.
BACKEND      := $(COMPOSE) run --rm --no-deps backend
BACKEND_DB   := $(COMPOSE) run --rm backend
# The same container, but with the backend folder writable (for formatting and locking).
BACKEND_RW   := docker run --rm -v "$(ROOT)/app/backend":/app -e RUFF_CACHE_DIR=/tmp/ruff

.DEFAULT_GOAL := help
.PHONY: help fmt fmt-check validate lint gitleaks gitleaks-staged checkov semgrep \
        semgrep-test trivy scan check hooks sweep up down logs ps reset-db seed openapi \
        build lock fmt-backend lint-backend test-backend audit-backend hadolint \
        image-build image-scan check-backend check-images

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

lint: ## tflint on every stack
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
	$(DOCKER_RUN) $(CHECKOV_IMAGE) -d /src --framework terraform github_actions dockerfile \
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

up: build ## Start the app on the laptop: backend on http://localhost:8080
	$(COMPOSE) up --detach --wait backend
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
	$(COMPOSE) up --detach --wait backend

seed: ## Write the seed data again (same keys, so nothing is duplicated)
	$(BACKEND_DB) python scripts/seed.py

openapi: ## Write the API description to .cache/openapi.json
	@mkdir -p .cache
	$(BACKEND) python scripts/export_openapi.py > .cache/openapi.json
	@echo "Written: .cache/openapi.json"

# Built with plain `docker build`, not `docker compose build`: Compose then finds the
# image by its name. (Compose's own build ignored the network setting when tested.)
build: ## Build the backend dev image
	$(DOCKER_BUILD) --quiet --target dev --tag productivity-app-backend:dev app/backend

# ---- Backend checks -----------------------------------------------------------------

lock: ## Recreate app/backend/uv.lock after changing pyproject.toml
	$(DOCKER_BUILD) --quiet --target base --tag productivity-app-backend:base app/backend
	$(BACKEND_RW) productivity-app-backend:base uv lock

fmt-backend: build ## Format the backend code and apply safe lint fixes
	$(BACKEND_RW) productivity-app-backend:dev sh -c "ruff format . && ruff check --fix ."

lint-backend: build ## ruff (format and lint) and mypy
	$(BACKEND) sh -c "ruff format --check . && ruff check . && mypy"

test-backend: build ## pytest, including the tests that use DynamoDB Local
	$(BACKEND_DB) pytest

# pip-audit only reads a list of packages; it installs nothing. `uv export` writes that
# list from uv.lock, with hashes. Development tools are included: they run on the
# laptop and in CI, so a vulnerable one matters too.
audit-backend: build ## Known vulnerabilities in the Python packages
	$(BACKEND) sh -c "uv export --quiet --locked --format requirements-txt --output-file /tmp/requirements.txt \
	  && pip-audit --requirement /tmp/requirements.txt --require-hashes --disable-pip --timeout 60"

# ---- Images -------------------------------------------------------------------------

hadolint: ## Lint the Dockerfiles
	$(DOCKER_RUN) $(HADOLINT_IMAGE) hadolint app/backend/Dockerfile

image-build: ## Build the backend image that ships (the runtime stage)
	$(DOCKER_BUILD) --quiet --target runtime --tag productivity-app-backend:runtime app/backend

# The image is saved to a file and Trivy scans the file. The other way, giving the Trivy
# container the Docker socket, would hand it control over Docker on this machine.
# --ignore-unfixed: a vulnerability with no fix yet is reported by nobody's action but
# time; the weekly base image update picks the fix up when it exists.
image-scan: image-build ## Scan the shipped image for vulnerabilities and secrets
	@mkdir -p .cache/images .cache/trivy
	docker save --output .cache/images/backend.tar productivity-app-backend:runtime
	$(DOCKER_RUN) -e TRIVY_CACHE_DIR=/src/.cache/trivy $(TRIVY_IMAGE) image \
	  --input /src/.cache/images/backend.tar --scanners vuln,secret \
	  --severity HIGH,CRITICAL --ignore-unfixed --ignorefile /src/.trivyignore.yaml \
	  --exit-code 1 --quiet

check-backend: lint-backend test-backend audit-backend ## All backend checks

check-images: hadolint image-scan ## All image checks

check: fmt-check validate lint scan check-backend check-images ## Everything CI runs
	@echo "All checks passed."

hooks: ## Install the pre-commit hooks (once per clone)
	uv tool install pre-commit==$(PRE_COMMIT_VERSION)
	pre-commit install

sweep: ## Read-only check for running AWS resources
	./scripts/sweep.sh
