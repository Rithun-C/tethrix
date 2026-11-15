# tflint settings, shared by every Terraform stack.
#
# tflint finds mistakes that `terraform validate` cannot: an instance type that does not
# exist, a variable nobody uses, a module without a pinned version.

config {
  call_module_type = "local"
}

# The built-in Terraform rules, all of them (the default is only the "recommended" set).
plugin "terraform" {
  enabled = true
  preset  = "all"
}

# AWS-specific rules. Downloaded by `tflint --init`, which checks the plugin's signature.
# https://github.com/terraform-linters/tflint-ruleset-aws/releases/tag/v0.50.0
plugin "aws" {
  enabled = true
  version = "0.50.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Off: this rule wants every folder to have a main.tf. Our stacks are split into files
# by topic instead (budgets.tf, cloudtrail.tf), which is easier to read. Modules in
# infra/modules/ still follow the main.tf / variables.tf / outputs.tf layout by convention.
rule "terraform_standard_module_structure" {
  enabled = false
}
