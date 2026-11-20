# Dependency policy

- Task: B1-06
- Requirements: SR-80, SR-81, SR-82, SR-83
- Threat: T-008 (malicious or vulnerable dependency)

A dependency is any code we did not write but run: Python and npm packages, Docker
images, GitHub Actions, Terraform providers, and the scanners themselves. Each one runs
with our permissions, so a bad one can steal what we can reach. The background is in
`docs/theory/supply-chain-security.md`.

## 1. Pin everything

"Pinning" means writing down the exact version, so the same code runs tomorrow as today.

| Kind | How it is pinned | Where |
|---|---|---|
| Scanner images | Tag and sha256 digest | `tools/versions.env` |
| App base images (from B2) | Tag and sha256 digest | `Dockerfile` |
| GitHub Actions | Full commit SHA, version in a comment | `.github/workflows/*.yml` |
| pre-commit hook repos | Full commit SHA, version in a comment | `.pre-commit-config.yaml` |
| Terraform providers | Exact version, plus hashes in the lock file | `versions.tf`, `.terraform.lock.hcl` |
| tflint plugin | Exact version (tflint checks its signature) | `.tflint.hcl` |
| Python packages (from B2) | Exact versions with hashes in a lockfile, managed with uv (not pip), installed with `uv sync --locked` | `pyproject.toml`, `uv.lock` |
| npm packages (from B2) | Exact versions in a lockfile with a hash per package, installed with `npm ci`; install scripts off (`ignore-scripts=true`) | `package.json`, `package-lock.json`, `.npmrc` |

Never `latest`, never a version range, never a tag alone for an image or an action.

Why a digest or SHA and not a tag: a tag is a label the publisher can move to different
content at any time. If the publisher's account is stolen, the attacker moves the tag and
everyone using it runs the attacker's code. A digest or SHA is a fingerprint of the
content. Different content has a different fingerprint, so it cannot be swapped.

## 2. Before adding any dependency (SR-81)

Write the answers in the bolt's journal entry.

1. Is it needed? Could the standard library or a few lines of our own code do it?
2. Does it exist on the official registry (PyPI, npm, Docker Hub, GitHub)?
3. Is the name spelled exactly right? Attackers publish look-alike names
   (`reqeusts` for `requests`).
4. Is the publisher the real one? The registry page should link to the project's
   repository, and the repository should link back.
5. Is it maintained? A release in the last year, and issues being answered.
6. Is it widely used? Download counts and stars are weak signals, but a package with
   almost none deserves a closer look.
7. Is the licence acceptable? MIT, BSD, Apache-2.0 and ISC are fine. Ask before using
   GPL or AGPL code, or code with no licence.
8. Is the version at least two weeks old? Most malicious releases are found and
   removed within days; two weeks leaves a margin (owner's decision, 2026-11-20; it was
   one week before). If a fix is only in a newer release, wait and note the date it
   becomes usable. This covers Docker images and GitHub Actions too. For Python it is
   enforced: `exclude-newer = "14 days"` in `app/backend/pyproject.toml` makes uv ignore
   anything newer when it writes the lockfile. For npm it is `min-release-age=14` in
   `app/frontend/.npmrc`.

This applies to Claude's suggestions too. An AI model can suggest a package name that
does not exist, and attackers register such names. Every suggested package is checked
against the registry before it is added.

## 3. Updates

- Dependabot opens pull requests once a week (`.github/dependabot.yml`): GitHub Actions
  now; Docker, uv and npm from B2. It waits 7 days after a release.
- A Dependabot pull request passes the same CI checks as any other. Read the release
  notes before merging. Never merge a red pull request.
- Security alerts (Dependabot alerts on GitHub) are handled within a week for High and
  Critical, and logged in `docs/security/findings-log.md`.

### Updating a scanner

Dependabot does not read `tools/versions.env`. Check once a month:

1. Open the tool's releases page (the links are in `tools/versions.env`). Pick the newest
   release that is at least a week old.
2. Get the digest: `docker buildx imagetools inspect <image>:<tag>` and copy the
   `Digest:` line.
3. Update the line in `tools/versions.env` (tag and digest together).
4. Run `make check`. New versions bring new rules, so new findings are normal: fix them
   or log them as accepted, in the same pull request.

## 4. What fails the build (SR-82)

| Tool | Fails on |
|---|---|
| gitleaks | Any finding |
| terraform fmt, validate | Any error |
| tflint | Any issue |
| checkov | Any failed check that has no written skip |
| Semgrep | Any finding from the public rules or our own |
| Trivy | High or Critical |
| pip-audit, npm audit (from B2) | High or Critical |

pip-audit is only a scanner. It does not install anything, so it stays even though the
backend uses uv: it reads the package list that `uv export` writes from `uv.lock`.

A finding can be accepted instead of fixed only with a comment in the code that gives
the reason (`#checkov:skip=...`, `#trivy:ignore:...`, `# nosemgrep: ...`) and, if it is
High or Critical, a row in the findings log.
