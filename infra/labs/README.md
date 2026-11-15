# infra/labs

One folder per time-boxed lab. Each lab is its own Terraform stack with its own state
file, so `terraform destroy` in a lab cannot touch the app or the bootstrap stack.

## Starting a lab

1. Copy the template: `cp -R infra/labs/_template infra/labs/<name>`
2. In the new folder: set `Stack = "lab-<name>"` in `providers.tf`, and the state key
   `labs/<name>/terraform.tfstate` in `backend.hcl.example`.
3. Fill in `README.md` down to "Approval". Do not apply before the owner has approved.
4. Add the folder to `TF_STACKS` in the `Makefile` so the checks cover it.

The process and the reasons are in `docs/inception/11-cost-model.md`, section 5.

## Labs

| Folder | What | Cost |
|---|---|---|
| `kind/` | Kubernetes on the laptop (B2-07). Not Terraform and nothing in AWS: a cluster config and manifests, checked by checkov, Trivy and Semgrep | None |
