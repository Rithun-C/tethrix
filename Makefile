# Shortcuts for the checks every change must pass. `make help` lists them.
# CI runs these same targets, so a pass here means a pass there.
#
# The scanners run as Docker images pinned in tools/versions.env. Docker Desktop must be
# running. Terraform itself runs from the laptop install.

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

.DEFAULT_GOAL := help
.PHONY: help fmt fmt-check validate lint gitleaks gitleaks-staged checkov semgrep \
        semgrep-test trivy scan check hooks sweep

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
	$(DOCKER_RUN) $(CHECKOV_IMAGE) -d /src --framework terraform github_actions \
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
	  --skip-files '**/tfplan' .

scan: gitleaks checkov semgrep trivy ## All four security scanners

check: fmt-check validate lint scan ## Everything CI runs
	@echo "All checks passed."

hooks: ## Install the pre-commit hooks (once per clone)
	uv tool install pre-commit==$(PRE_COMMIT_VERSION)
	pre-commit install

sweep: ## Read-only check for running AWS resources
	./scripts/sweep.sh
