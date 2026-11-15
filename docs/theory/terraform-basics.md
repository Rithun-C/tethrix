# Terraform basics, explained through G-06

Written 2026-11-12 after the first Terraform apply. Goes with task B1-08 (Terraform state,
locking, drift, modules), which will go deeper later.

## 1. What Terraform is

Terraform lets you describe infrastructure in text files, and then makes AWS match them.

You write the end result you want ("a private, encrypted S3 bucket with versioning"),
not the steps to get there. This is called declarative. Terraform works out the steps:
what to create, change or delete, and in what order.

Why this beats clicking in the console:

- The files are the record of what exists. Nothing is forgotten.
- Every change is reviewed (with `plan`) before it happens.
- The same files can rebuild everything, or destroy everything, on demand.
- Changes are tracked in git like any other code.

## 2. The four pieces

```
 Your .tf files          Terraform           Provider plugin            AWS
 (what you want)  --->   compares    --->    (translates to     --->   (what exists)
                          and plans           AWS API calls)
                             |
                         State file
                     (what Terraform
                      remembers it built)
```

- Code: the `.tf` files in `infra/bootstrap/`.
- Provider: a plugin downloaded from the Terraform Registry. The AWS provider knows how
  to turn `aws_s3_bucket` into real AWS API calls. We pin it to version 6.71.0.
- State: Terraform's memory. A JSON file that links each block in your code to the real
  thing in AWS. For example: `aws_s3_bucket.state` -> bucket `productivity-app-tfstate-...`.
  Without state, Terraform cannot tell which real bucket belongs to which block.
- AWS: the real resources.

## 3. Reading the code

Every block has the same shape: `kind "type" "name" { settings }`.

| Block | What it does | Example in G-06 |
|---|---|---|
| `terraform` | Settings for Terraform itself: versions, backend | `versions.tf` |
| `provider` | Configures a plugin: region, default tags | `providers.tf` |
| `resource` | Something Terraform creates and owns | `aws_s3_bucket.state` |
| `data` | Something Terraform only reads | `aws_caller_identity.current` (your account ID) |
| `variable` | An input with a default value | `var.region` |
| `locals` | A named value computed inside the code | `local.state_bucket_name` |
| `output` | A value printed after apply | `state_bucket_name` |

References connect blocks. `bucket = aws_s3_bucket.state.id` means "use the ID of the
bucket created above". Terraform reads these references to work out the order: the
bucket must exist before its versioning setting can be applied. This is called the
dependency graph. `depends_on` adds an order Terraform cannot see from references alone.

## 4. What each command did

### `export AWS_PROFILE=admin`

Tells the AWS CLI and Terraform which profile to use. Terraform reads the same
credentials the CLI got from `aws login`. No keys are written anywhere.

### `aws sts get-caller-identity`

Asks AWS "who am I?". A safety check that you are acting as `admin` in the right account
before Terraform does anything.

### `terraform init`

Prepares the folder. It changes nothing in AWS.

1. Reads `versions.tf` and downloads AWS provider 6.71.0 into `.terraform/`.
2. Checks the download against the hashes in `.terraform.lock.hcl`. If they don't match,
   it refuses to run. This protects against a tampered plugin.
3. Sets up the backend (where state is stored). At this point there was no backend
   block, so it used the default: a local file, `terraform.tfstate`.

### `terraform plan -out=tfplan`

Works out what would change. It changes nothing in AWS.

1. Refresh: asks AWS for the current details of everything already in state. On the
   first run the state was empty, so there was nothing to check.
2. Runs data sources: called AWS to read your account ID, to build the bucket name.
3. Compares your code with the state and lists the differences.
4. Saves that exact list to the file `tfplan`.

The symbols in a plan:

| Symbol | Meaning |
|---|---|
| `+` | create |
| `~` | change in place |
| `-` | destroy |
| `-/+` | destroy and recreate (replace) |

"(known after apply)" means the value is only known once AWS creates the thing, for
example a resource's ID.

Your plan said `7 to add`: the bucket plus its six settings resources.

Why `-out=tfplan`: `apply` then does exactly what you reviewed, even if something
changed in between.

### `terraform apply tfplan`

Makes the changes.

1. Makes the AWS API calls in dependency order: the bucket first, then its settings.
   Settings that don't depend on each other run in parallel. The bucket policy waited for
   the public access block because of `depends_on`.
2. After each resource is created, records it in state.

Without a saved plan file, `apply` plans again and asks you to type `yes`.

### `terraform output -raw state_bucket_name`

Reads an output value from state and prints it. `-raw` prints it without quotes.

### `backend.tf` and `backend.hcl`

The backend decides where state is stored. `backend.tf` says "use S3".
`backend.hcl` gives the details: bucket, key (the file path inside the bucket), region,
encryption and locking.

They are split because backend blocks cannot use variables, and the bucket name
contains your account ID. Keeping it in `backend.hcl`, which git ignores, keeps the ID out
of the public repo. This is called partial configuration.

### `terraform init -backend-config=backend.hcl -migrate-state`

Changes the backend from local to S3.

1. Reads the new backend settings.
2. Copies the local state file to `s3://<bucket>/bootstrap/terraform.tfstate`.
3. From now on, every `plan` and `apply` in this folder reads and writes state in S3.

Locking: with `use_lockfile = true`, each `plan` or `apply` first writes a small
`.tflock` file next to the state in S3, and deletes it when done. A second run that
starts at the same time sees the lock and waits or fails. This stops two runs from
corrupting the state.

### `terraform plan` (should say "No changes")

Proves the move worked. Terraform read the state from S3, refreshed it from AWS, compared
it to the code, and found nothing to do. Code, state and AWS all agree.

### `rm terraform.tfstate terraform.tfstate.backup tfplan`

Removes the local copies. State now lives only in S3, which is versioned and encrypted.
A copy on your laptop could go stale or leak.

## 5. Files in the folder now

| File | Committed to git? | Why |
|---|---|---|
| `*.tf` | Yes | The code |
| `.terraform.lock.hcl` | Yes | Pins exact provider versions and hashes |
| `backend.hcl.example` | Yes | Shows the format without the account ID |
| `backend.hcl` | No | Contains the account ID |
| `.terraform/` | No | Downloaded plugins; `init` recreates it |

## 6. The loop for every future change

1. Edit the `.tf` files.
2. `terraform plan` and read every line.
3. `terraform apply` only if the plan matches what you expect.

Drift: if anyone changes a Terraform-managed resource in the console, the next `plan`
shows a difference and offers to put it back. This is one reason for the no-console rule.

## 7. Safe things to try (free, change nothing)

```
cd infra/bootstrap
terraform state list                         # every resource Terraform manages here
terraform state show aws_s3_bucket.state     # everything Terraform knows about the bucket
terraform console                            # type local.state_bucket_name, then exit
```

An experiment that shows a plan without applying it:

1. In `variables.tf`, change `noncurrent_version_days` default from 90 to 60.
2. Run `terraform plan`. It shows `~` (change in place) on the lifecycle rule only.
3. Change it back to 90 and run `terraform plan` again. It says "No changes".
   Do not apply.
