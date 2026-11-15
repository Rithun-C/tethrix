# Git repo, GitHub settings and CI

- Tasks: B1-01, B1-03, B1-05
- Design: `docs/bolts/B1-foundation.md`

## Purpose

Create the public GitHub repo so that nothing secret is ever pushed, and so that nothing
reaches `main` without passing the checks.

## When to use it

Once, in bolt B1. Part D is reused whenever a laptop gets a fresh clone.

## Prerequisites

- Docker Desktop is running (the scanners are containers).
- `make check` passes.
- A GitHub account with two-factor authentication on.

## Part A: before the first commit

1. On github.com: Settings > Emails. Tick "Keep my email addresses private" and "Block
   command line pushes that expose my email". Copy the no-reply address shown there. It
   looks like `12345678+username@users.noreply.github.com`.
   Why: every commit carries an author email, and the repo is public.
2. Review the new files (listed in `docs/bolts/B1-foundation.md`, section 8).
3. Ask Claude to make the first commit, and give it the no-reply address and the GitHub
   username. Claude then runs:

   ```sh
   git init -b main
   git config user.name  "<GitHub username>"
   git config user.email "<no-reply address>"
   git add -A
   make gitleaks-staged        # must say "no leaks found"
   git commit -m "..."
   ```

   The name and email are set for this repo only (no `--global`).

Verify: `git log --format='%an %ae'` shows only the no-reply address.
`git ls-files | grep -E 'tfvars$|backend.hcl$|tfplan|tfstate'` prints nothing.

## Part B: create the repo and push

4. On github.com: New repository. Owner: you. Visibility: Public. Leave "Add a README",
   ".gitignore" and "licence" off; the repo must start empty.
5. Sign git in to GitHub. The simplest way is the GitHub CLI:

   ```sh
   brew install gh
   gh auth login        # GitHub.com, HTTPS, "Login with a web browser"
   ```

   The login token is kept in the macOS keychain, not in a file.
6. Push:

   ```sh
   git remote add origin https://github.com/<username>/<repo>.git
   git push -u origin main
   ```

Verify: the repo page shows the files, and the Actions tab shows a `static-checks` run.
Wait for it to finish green.

## Part C: repo settings (web)

7. Settings > Advanced Security. Turn on:
   - Private vulnerability reporting
   - Dependabot alerts
   - Secret Protection (secret scanning), and inside it Push protection
8. Settings > Actions > General:
   - "Allow <you>, and select non-<you>, actions and reusable workflows". Tick "Allow
     actions created by GitHub". In the list box add `hashicorp/setup-terraform@*`.
   - Tick "Require actions to be pinned to a full-length commit SHA".
   - Approval for running fork pull request workflows: "Require approval for all
     external contributors".
   - Workflow permissions: "Read repository contents and packages permissions". Leave
     "Allow GitHub Actions to create and approve pull requests" unticked.
9. Settings > Rules > Rulesets > New branch ruleset:
   - Name: `main`. Enforcement status: Active. Bypass list: empty.
   - Target branches: Include default branch.
   - Tick: Restrict deletions; Block force pushes; Require a pull request before
     merging (required approvals: 0); Require status checks to pass, and add the check
     `all-checks`. The check can only be chosen after CI has run once (step 6).

Why 0 approvals: GitHub does not let you approve your own pull request, so 1 would lock
you out. The pull request still forces every change through CI.

## Part D: hooks on the laptop

10. `make hooks` (installs pre-commit and connects it to this clone).

Verify: `pre-commit run --all-files` passes.

## Part E: prove the gates work

11. A direct push to `main` must be refused:

    ```sh
    git commit --allow-empty -m "test: direct push"
    git push            # expected: rejected by the ruleset
    git reset --hard origin/main
    ```

12. A failing pull request must be blocked. Use a formatting error, never a fake
    secret (anything pushed stays in GitHub's history):

    ```sh
    git switch -c test/ci-blocks-bad-format
    printf 'variable "x" {\ntype=string\n}\n' > infra/app/ci_test.tf
    git add infra/app/ci_test.tf
    git commit --no-verify -m "test: badly formatted file"
    git push -u origin test/ci-blocks-bad-format
    ```

    `--no-verify` skips the pre-commit hook on purpose, to show that CI still catches it.
    Open a pull request on GitHub. Expected: the `terraform` job and `all-checks` fail,
    and the merge button is blocked. Then close the pull request, delete the branch on
    GitHub, and locally:

    ```sh
    git switch main
    git branch -D test/ci-blocks-bad-format
    ```

## Daily use after this

```sh
git switch -c <short-branch-name>
# change files
make check
git add -A && git commit -m "..."
git push -u origin <short-branch-name>
# open a pull request, wait for green, merge, then:
git switch main && git pull
```

## Undo

- Wrong file committed but not pushed: `git reset --soft HEAD~1`, fix, commit again.
- A secret or the account ID was pushed: treat it as leaked. Rotate the secret first.
  Deleting the commit does not remove it from GitHub or from anyone who already copied
  it. Log it in `docs/security/findings-log.md`.
