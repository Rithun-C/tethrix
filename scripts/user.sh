#!/usr/bin/env bash
# Admin tasks for user accounts (B4-08, I-01: only the admin creates accounts).
# Run by the owner with their AWS profile, through `make user-create` and friends,
# which pass the pool ID and table name from the Terraform outputs.
#
# Users are data, not infrastructure, so these are CLI calls, not Terraform (I-13).
# Email addresses are typed on the command line and never written into the repo.
#
# Usage:
#   scripts/user.sh create  POOL_ID TABLE EMAIL TIME_ZONE
#   scripts/user.sh disable POOL_ID TABLE EMAIL
#   scripts/user.sh delete  POOL_ID TABLE EMAIL

set -euo pipefail

action="${1:?create, disable or delete}"
pool="${2:?Cognito user pool ID}"
table="${3:?DynamoDB table name}"
email="${4:?email address}"

# Simple shape checks, so a typo fails here and not halfway through.
if ! [[ "$email" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo "That does not look like an email address: $email" >&2
  exit 1
fi
if ! [[ "$pool" =~ ^us-east-1_[A-Za-z0-9]+$ ]]; then
  echo "That does not look like a user pool ID in us-east-1: $pool" >&2
  exit 1
fi

# The user's ID (`sub`): the key of everything they own (USER#<sub>, I-08).
user_sub() {
  # The backticks are JMESPath (the AWS CLI query language), not the shell.
  # shellcheck disable=SC2016
  aws cognito-idp admin-get-user --user-pool-id "$pool" --username "$email" \
    --query 'UserAttributes[?Name==`sub`].Value | [0]' --output text
}

profile_key() {
  printf '{"PK":{"S":"USER#%s"},"SK":{"S":"PROFILE"}}' "$1"
}

case "$action" in
  create)
    tz="${5:?time zone, for example Asia/Kolkata}"
    if ! [[ "$tz" =~ ^[A-Za-z_]+(/[A-Za-z0-9_+-]+)*$ ]]; then
      echo "That does not look like a time zone name (for example Asia/Kolkata): $tz" >&2
      exit 1
    fi

    # 1. The Cognito user. Cognito emails a temporary password (valid 3 days); at first
    #    sign-in the user sets a new password and an authenticator app.
    # shellcheck disable=SC2016  # backticks are JMESPath, not the shell
    sub=$(aws cognito-idp admin-create-user --user-pool-id "$pool" --username "$email" \
      --user-attributes Name=email,Value="$email" Name=email_verified,Value=true \
      --desired-delivery-mediums EMAIL \
      --query 'User.Attributes[?Name==`sub`].Value | [0]' --output text)
    echo "Created the Cognito user. User ID: $sub"

    # 2. The profile item. Without it the API answers 401 (SR-03). Only written if it
    #    does not exist yet, so running this twice cannot overwrite anything.
    now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    item=$(printf '{"PK":{"S":"USER#%s"},"SK":{"S":"PROFILE"},"timeZone":{"S":"%s"},"createdAt":{"S":"%s"}}' \
      "$sub" "$tz" "$now")
    aws dynamodb put-item --table-name "$table" --item "$item" \
      --condition-expression 'attribute_not_exists(PK)'
    echo "Created the profile (time zone $tz). Cognito has emailed a temporary password."
    ;;

  disable)
    # Stops new sign-ins and revokes the user's refresh tokens. An access token already
    # issued keeps working until it expires (60 minutes at most, T-027).
    aws cognito-idp admin-disable-user --user-pool-id "$pool" --username "$email"
    aws cognito-idp admin-user-global-sign-out --user-pool-id "$pool" --username "$email"
    echo "Disabled and signed out everywhere. Undo with: aws cognito-idp admin-enable-user"
    ;;

  delete)
    # Profile first: from that moment the API refuses the user's tokens (SR-03), even
    # an access token that has not expired yet. B10 extends this to all their data.
    sub=$(user_sub)
    aws dynamodb delete-item --table-name "$table" --key "$(profile_key "$sub")"
    aws cognito-idp admin-delete-user --user-pool-id "$pool" --username "$email"
    echo "Deleted the profile and the Cognito user (user ID $sub)."
    ;;

  *)
    echo "Unknown action: $action (use create, disable or delete)" >&2
    exit 1
    ;;
esac
