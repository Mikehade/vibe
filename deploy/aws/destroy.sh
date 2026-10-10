#!/usr/bin/env bash
# Delete everything deploy.sh created (stack, web bucket contents, ECR images). Irreversible.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STACK="${STACK:-vibe}"; REPO="${REPO:-vibe-api}"
REGION="${AWS_REGION:-$(grep -E '^AWS_REGION=' "$ROOT/backend/.env" 2>/dev/null | cut -d= -f2- || true)}"; export AWS_REGION="${REGION:-us-east-1}"
read -r -p "Delete stack '$STACK' (database, App Runner, CloudFront, bucket) in $AWS_REGION? Type 'delete': " ans
[ "$ans" = "delete" ] || { echo "Cancelled."; exit 0; }
BUCKET="$(aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='WebBucketName'].OutputValue" --output text 2>/dev/null || true)"
[ -n "$BUCKET" ] && [ "$BUCKET" != "None" ] && aws s3 rm "s3://$BUCKET" --recursive >/dev/null || true
aws cloudformation delete-stack --stack-name "$STACK"
echo "Waiting for the stack to delete (CloudFront can take ~10 minutes)…"
aws cloudformation wait stack-delete-complete --stack-name "$STACK"
aws ecr delete-repository --repository-name "$REPO" --force >/dev/null 2>&1 || true
rm -f "$ROOT/deploy/aws/outputs.env"
echo "Done."
