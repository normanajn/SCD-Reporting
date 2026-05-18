#!/usr/bin/env bash
set -euo pipefail

# Fill these in before running.
AWS_REGION="us-east-1"
INSTANCE_ID="i-xxxxxxxxxxxxxxxxx"
HOSTED_ZONE_ID="Z1234567890ABC"
RECORD_NAME="scd-reporting.example.org."
TTL="300"

# Optional: set this to reuse an existing Elastic IP allocation.
# Leave empty to allocate a new Elastic IP.
EXISTING_ALLOCATION_ID=""

# Set to "true" if you want to move an existing Elastic IP association.
ALLOW_REASSOCIATION="false"

require_value() {
    local name="$1"
    local value="$2"

    if [ -z "$value" ] || [[ "$value" == *xxxxxxxx* ]] || [[ "$value" == Z1234567890ABC ]]; then
        echo "Set $name at the top of this script before running." >&2
        exit 1
    fi
}

require_command() {
    local command_name="$1"

    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
}

require_command aws
require_value AWS_REGION "$AWS_REGION"
require_value INSTANCE_ID "$INSTANCE_ID"
require_value HOSTED_ZONE_ID "$HOSTED_ZONE_ID"
require_value RECORD_NAME "$RECORD_NAME"

if [[ "$RECORD_NAME" != *. ]]; then
    RECORD_NAME="${RECORD_NAME}."
fi

echo "Checking EC2 instance exists: $INSTANCE_ID"
aws ec2 describe-instances \
    --region "$AWS_REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text >/dev/null

if [ -n "$EXISTING_ALLOCATION_ID" ]; then
    ALLOCATION_ID="$EXISTING_ALLOCATION_ID"
    echo "Using existing Elastic IP allocation: $ALLOCATION_ID"
else
    echo "Allocating a new Elastic IP..."
    ALLOCATION_ID="$(
        aws ec2 allocate-address \
            --region "$AWS_REGION" \
            --domain vpc \
            --query 'AllocationId' \
            --output text
    )"
    echo "Allocated Elastic IP: $ALLOCATION_ID"
fi

ASSOCIATE_ARGS=(
    ec2 associate-address
    --region "$AWS_REGION"
    --instance-id "$INSTANCE_ID"
    --allocation-id "$ALLOCATION_ID"
)

if [ "$ALLOW_REASSOCIATION" = "true" ]; then
    ASSOCIATE_ARGS+=(--allow-reassociation)
fi

echo "Associating Elastic IP with instance..."
aws "${ASSOCIATE_ARGS[@]}" >/dev/null

PUBLIC_IP="$(
    aws ec2 describe-addresses \
        --region "$AWS_REGION" \
        --allocation-ids "$ALLOCATION_ID" \
        --query 'Addresses[0].PublicIp' \
        --output text
)"

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" = "None" ]; then
    echo "Could not determine public IP for allocation: $ALLOCATION_ID" >&2
    exit 1
fi

CHANGE_BATCH="$(
    mktemp "${TMPDIR:-/tmp}/route53-change-batch.XXXXXX.json"
)"
trap 'rm -f "$CHANGE_BATCH"' EXIT

cat > "$CHANGE_BATCH" <<EOF
{
  "Comment": "Point ${RECORD_NAME} to EC2 instance ${INSTANCE_ID}",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "${RECORD_NAME}",
        "Type": "A",
        "TTL": ${TTL},
        "ResourceRecords": [
          {
            "Value": "${PUBLIC_IP}"
          }
        ]
      }
    }
  ]
}
EOF

echo "Updating Route 53 A record: $RECORD_NAME -> $PUBLIC_IP"
CHANGE_ID="$(
    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch "file://$CHANGE_BATCH" \
        --query 'ChangeInfo.Id' \
        --output text
)"

echo "Waiting for Route 53 change to sync: $CHANGE_ID"
aws route53 wait resource-record-sets-changed --id "$CHANGE_ID"

echo "Done."
echo "Elastic IP allocation: $ALLOCATION_ID"
echo "A record: ${RECORD_NAME} -> ${PUBLIC_IP}"
