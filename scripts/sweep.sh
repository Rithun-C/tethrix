#!/usr/bin/env bash
# "What is running?" sweep. Read-only: it only lists and describes, never changes anything.
# Every call it makes is free. It does not call Cost Explorer.
#
# Usage:
#   export AWS_PROFILE=admin
#   bash scripts/sweep.sh            # us-east-1 only
#   bash scripts/sweep.sh --all      # also checks EC2, EIPs and NAT gateways in every region
#
# Each line says OK (nothing found) or CHECK (something found, with names).
# CHECK is not always bad: see "Expected items" in docs/runbooks/session-checklist.md.

set -u
HOME_REGION="us-east-1"
REGION="$HOME_REGION"
FOUND=0

# Prints OK or CHECK for one item.
# $1 = label, $2 = command output (whitespace-separated names, or empty)
report() {
  local label="$1" out
  out="$(echo "$2" | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')"
  if [ -z "$out" ] || [ "$out" = "None" ]; then
    printf "  OK     %s\n" "$label"
  else
    printf "  CHECK  %s: %s\n" "$label" "$out"
    FOUND=$((FOUND + 1))
  fi
}

# Runs an AWS CLI command in text mode. Errors (for example a service not enabled)
# count as "nothing found", but are shown so they are not silently hidden.
q() {
  local out
  if ! out="$(aws "$@" --region "$REGION" --output text 2>&1)"; then
    # AWS CLI errors start with a blank line, so take the first non-empty line.
    out="$(printf '%s\n' "$out" | grep -m1 -v '^[[:space:]]*$')"
    case "$out" in
      *NotFound*|*not\ subscribed*|*InvalidAccessException*|*not\ enabled*) echo "" ;;
      *) echo "ERROR: ${out}" ;;
    esac
    return
  fi
  echo "$out"
}

echo "Identity: $(aws sts get-caller-identity --query Arn --output text)"
echo "Region:   ${REGION}"
echo

echo "Hourly-billed resources (destroy these at the end of every session):"
report "EC2 instances (not terminated)" "$(q ec2 describe-instances \
  --filters Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId')"
report "Elastic IPs" "$(q ec2 describe-addresses --query 'Addresses[].PublicIp')"
report "Public IPv4 on network interfaces" "$(q ec2 describe-network-interfaces \
  --query 'NetworkInterfaces[?Association.PublicIp].NetworkInterfaceId')"
report "NAT gateways" "$(q ec2 describe-nat-gateways \
  --filter Name=state,Values=pending,available --query 'NatGateways[].NatGatewayId')"
report "VPC endpoints" "$(q ec2 describe-vpc-endpoints --query 'VpcEndpoints[].VpcEndpointId')"
report "Load balancers" "$(q elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerName')"
report "RDS instances" "$(q rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier')"
report "RDS/Aurora clusters" "$(q rds describe-db-clusters --query 'DBClusters[].DBClusterIdentifier')"
report "ECS clusters" "$(q ecs list-clusters --query 'clusterArns[]')"
report "EKS clusters" "$(q eks list-clusters --query 'clusters[]')"
report "GuardDuty detectors" "$(q guardduty list-detectors --query 'DetectorIds[]')"
report "Security Hub" "$(q securityhub describe-hub --query 'HubArn')"
report "Config recorders" "$(q configservice describe-configuration-recorders \
  --query 'ConfigurationRecorders[].name')"
report "Inspector (enabled scans)" "$(q inspector2 batch-get-account-status \
  --query "accounts[?state.status=='ENABLED'].accountId")"
report "WAF web ACLs (CloudFront)" "$(q wafv2 list-web-acls --scope CLOUDFRONT --query 'WebACLs[].Name')"
report "WAF web ACLs (regional)" "$(q wafv2 list-web-acls --scope REGIONAL --query 'WebACLs[].Name')"
echo

echo "Storage and monthly-billed resources:"
report "EBS volumes" "$(q ec2 describe-volumes --query 'Volumes[].VolumeId')"
report "EBS snapshots (yours)" "$(q ec2 describe-snapshots --owner-ids self --query 'Snapshots[].SnapshotId')"
report "RDS manual snapshots" "$(q rds describe-db-snapshots --snapshot-type manual \
  --query 'DBSnapshots[].DBSnapshotIdentifier')"
report "KMS keys you created" "$(q kms list-aliases \
  --query "Aliases[?!starts_with(AliasName, 'alias/aws/')].AliasName")"
report "Secrets Manager secrets" "$(q secretsmanager list-secrets --query 'SecretList[].Name')"
report "ECR repositories" "$(q ecr describe-repositories --query 'repositories[].repositoryName')"
report "S3 buckets" "$(aws s3api list-buckets --query 'Buckets[].Name' --output text 2>&1)"
echo

echo "Side resources that console wizards leave behind (lesson from F-001):"
report "Lambda functions" "$(q lambda list-functions --query 'Functions[].FunctionName')"
report "Log groups" "$(q logs describe-log-groups --query 'logGroups[].logGroupName')"
report "Log groups WITHOUT retention" "$(q logs describe-log-groups \
  --query 'logGroups[?!retentionInDays].logGroupName')"
report "IAM roles (not AWS service-linked)" "$(aws iam list-roles \
  --query "Roles[?!starts_with(Path, '/aws-service-role/')].RoleName" --output text 2>&1)"
report "IAM policies you created" "$(aws iam list-policies --scope Local \
  --query 'Policies[].PolicyName' --output text 2>&1)"
report "IAM users" "$(aws iam list-users --query 'Users[].UserName' --output text 2>&1)"
report "Access keys on admin (should be none)" "$(aws iam list-access-keys --user-name admin \
  --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>&1)"
report "Security groups (not default)" "$(q ec2 describe-security-groups \
  --query "SecurityGroups[?GroupName!='default'].GroupName")"
echo

if [ "${1:-}" = "--all" ]; then
  echo "Other regions (EC2 instances, Elastic IPs, NAT gateways). Should all be OK:"
  for r in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
    [ "$r" = "$HOME_REGION" ] && continue
    REGION="$r"
    report "${r} EC2 instances" "$(q ec2 describe-instances \
      --filters Name=instance-state-name,Values=pending,running,stopping,stopped \
      --query 'Reservations[].Instances[].InstanceId')"
    report "${r} Elastic IPs" "$(q ec2 describe-addresses --query 'Addresses[].PublicIp')"
    report "${r} NAT gateways" "$(q ec2 describe-nat-gateways \
      --filter Name=state,Values=pending,available --query 'NatGateways[].NatGatewayId')"
  done
  REGION="$HOME_REGION"
  echo
fi

echo "Done. ${FOUND} item(s) to check. Compare with 'Expected items' in the runbook."
