#!/usr/bin/env bash
# Deploy Vibe to AWS: ECR image → CloudFormation (RDS + App Runner + S3/CloudFront) → web app upload.
# Safe to re-run: every run ships a new backend image and the latest web build.
#
#   ./deploy/aws/deploy.sh               # uses backend/.env for TMDB key / model ids / AWS creds
#   STACK=vibe-demo ./deploy/aws/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
STACK="${STACK:-vibe}"
REPO="${REPO:-vibe-api}"

say()  { printf "\033[1;33m→\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }
envv() { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true; }

# ── CloudFormation helper ────────────────────────────────────────────────
# Uses create-stack / update-stack directly (not `aws cloudformation deploy`, which crashes with
# "aws: [ERROR]: 'Status'" on some AWS CLI v2 versions). Recovers stacks left broken by earlier runs.
#   cfn_apply <stack-name> <template-file> Key=Value ...
cfn_failures() {
  # Show why the stack failed, oldest first. Never hide errors here — they are the diagnosis.
  local ev
  if ! ev="$(aws cloudformation describe-stack-events --stack-name "$1" \
      --query "reverse(StackEvents[?contains(ResourceStatus, 'FAILED')].[ResourceStatus,LogicalResourceId,ResourceStatusReason])" \
      --output text 2>&1)"; then
    printf "  (could not read stack events: %s)\n" "$ev"
    case "$ev" in *AccessDenied*|*not\ authorized*) printf "  Your AWS user is missing permissions. Attach the AdministratorAccess policy to it (IAM console → Users → your user → Add permissions).\n";; esac
    return
  fi
  if [ -z "$ev" ] || [ "$ev" = "None" ]; then
    printf "  (no failed events recorded — open CloudFormation → Stacks → %s → Events in the AWS console)\n" "$1"
    return
  fi
  printf "%s\n" "$ev" | head -12 | sed 's/^/  /'
  case "$ev" in
    *"Cannot have more than 0 builds"*|*"account is not authorized"*|*SubscriptionRequired*|*OptInRequired*)
      printf "\n  → This AWS account can't use that service yet (common on new accounts). Try BUILD=local, or ask AWS Support to enable it.\n" ;;
    *AccessDenied*|*not\ authorized*|*UnauthorizedOperation*)
      printf "\n  → Your AWS user lacks permissions for these resources. Attach AdministratorAccess to it\n    (IAM console → Users → your user → Add permissions → AdministratorAccess) and re-run.\n" ;;
  esac
}
cfn_delete() {
  # Delete a stack; if some resources refuse to delete (ROLLBACK_FAILED / DELETE_FAILED), retain them and finish.
  local name="$1"
  aws cloudformation delete-stack --stack-name "$name"
  if aws cloudformation wait stack-delete-complete --stack-name "$name" 2>/dev/null; then return 0; fi
  local stuck; stuck="$(aws cloudformation describe-stack-resources --stack-name "$name" \
    --query "StackResources[?ResourceStatus=='DELETE_FAILED'].LogicalResourceId" --output text 2>/dev/null || true)"
  if [ -n "$stuck" ] && [ "$stuck" != "None" ]; then
    say "Some resources in $name would not delete ($stuck) — leaving them in place and removing the stack"
    # shellcheck disable=SC2086
    aws cloudformation delete-stack --stack-name "$name" --retain-resources $stuck
    aws cloudformation wait stack-delete-complete --stack-name "$name" 2>/dev/null && return 0
  fi
  printf "\nWhy:\n"; cfn_failures "$name"
  die "Could not delete stack $name. Delete it in the CloudFormation console (Stacks → $name → Delete), then re-run."
}
cfn_apply() {
  local name="$1" tpl="$2"; shift 2
  local params; params="$(python3 -c 'import json,sys; print(json.dumps([{"ParameterKey":a.split("=",1)[0],"ParameterValue":a.split("=",1)[1]} for a in sys.argv[1:]]))' "$@")"
  local status; status="$(aws cloudformation describe-stacks --stack-name "$name" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo NONE)"
  case "$status" in
    ROLLBACK_COMPLETE|ROLLBACK_FAILED|CREATE_FAILED|DELETE_FAILED|REVIEW_IN_PROGRESS)
      say "Stack $name is in state $status from an earlier attempt — removing it first"
      cfn_delete "$name"
      status=NONE ;;
    *_IN_PROGRESS)
      say "Stack $name is busy ($status) — waiting for it to settle"
      aws cloudformation wait stack-update-complete --stack-name "$name" 2>/dev/null \
        || aws cloudformation wait stack-create-complete --stack-name "$name" 2>/dev/null || true
      status="$(aws cloudformation describe-stacks --stack-name "$name" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo NONE)" ;;
  esac
  if [ "$status" = "NONE" ]; then
    aws cloudformation create-stack --stack-name "$name" --template-body "file://$tpl" \
      --parameters "$params" --capabilities CAPABILITY_IAM >/dev/null
    if ! aws cloudformation wait stack-create-complete --stack-name "$name"; then
      printf "\nWhat failed:\n"; cfn_failures "$name"
      die "Creating $name failed (reasons above). Fix it and re-run — the failed stack is cleaned up automatically."
    fi
  else
    local out
    if ! out="$(aws cloudformation update-stack --stack-name "$name" --template-body "file://$tpl" \
        --parameters "$params" --capabilities CAPABILITY_IAM 2>&1)"; then
      case "$out" in
        *"No updates are to be performed"*) return 0 ;;
        *) die "Updating $name failed: $out" ;;
      esac
    fi
    if ! aws cloudformation wait stack-update-complete --stack-name "$name"; then
      printf "\nWhat failed:\n"; cfn_failures "$name"
      die "Updating $name failed and was rolled back (the previous version is still running)."
    fi
  fi
}

# ── Inputs ───────────────────────────────────────────────────────────────
for v in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE; do
  if [ -z "${!v:-}" ] && [ -n "$(envv $v)" ]; then export "$v=$(envv $v)"; fi
done
REGION="${AWS_REGION:-$(envv AWS_REGION)}"; REGION="${REGION:-us-east-1}"
export AWS_REGION="$REGION" AWS_DEFAULT_REGION="$REGION"
TMDB_API_KEY="${TMDB_API_KEY:-$(envv TMDB_API_KEY)}"
MODEL="${BEDROCK_MODEL_ID:-$(envv BEDROCK_MODEL_ID)}"; MODEL="${MODEL:-us.anthropic.claude-sonnet-4-6}"
FAST="${BEDROCK_FAST_MODEL_ID:-$(envv BEDROCK_FAST_MODEL_ID)}"; FAST="${FAST:-us.anthropic.claude-haiku-4-5-20251001-v1:0}"
DEFAULT_REGION="${DEFAULT_REGION:-$(envv DEFAULT_REGION)}"; DEFAULT_REGION="${DEFAULT_REGION:-US}"

command -v aws >/dev/null    || die "AWS CLI not found. Install: brew install awscli"
command -v npm >/dev/null    || die "Node.js/npm not found. Install: brew install node"
command -v python3 >/dev/null || die "python3 not found. Install: brew install python@3.12"
[ -n "$TMDB_API_KEY" ] && [ "$TMDB_API_KEY" != "your_tmdb_api_key" ] || die "TMDB_API_KEY missing (set it in backend/.env)"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" || die "AWS credentials not working. Run 'aws configure' or set keys in backend/.env"
ok "AWS account $ACCOUNT, region $REGION, stack $STACK"

# Permissions check: this deploy creates IAM roles, a database, CodeBuild, App Runner and CloudFront.
CALLER_ARN="$(aws sts get-caller-identity --query Arn --output text)"
case "$CALLER_ARN" in
  *":user/"*)
    IAM_USER="${CALLER_ARN##*/}"
    POLICIES="$( { aws iam list-attached-user-policies --user-name "$IAM_USER" --query 'AttachedPolicies[].PolicyName' --output text 2>/dev/null
                  for g in $(aws iam list-groups-for-user --user-name "$IAM_USER" --query 'Groups[].GroupName' --output text 2>/dev/null); do
                    aws iam list-attached-group-policies --group-name "$g" --query 'AttachedPolicies[].PolicyName' --output text 2>/dev/null; done; } | tr '\t' ' ')"
    case "$POLICIES" in
      *AdministratorAccess*) ok "IAM user $IAM_USER has AdministratorAccess" ;;
      *) say "IAM user $IAM_USER doesn't appear to have AdministratorAccess (found: ${POLICIES:-none visible})."
         say "If the deploy fails with AccessDenied, attach AdministratorAccess in IAM → Users → $IAM_USER → Add permissions." ;;
    esac ;;
  *":root"*) say "You're using the account root user. It works, but an IAM user with AdministratorAccess is safer." ;;
esac

# ── 1. Backend image → ECR (exactly one image is kept) ─────────────────
# BUILD=cloud (default): upload a ~1 MB source zip; AWS CodeBuild builds and pushes the image inside AWS.
#   Fast on slow home connections, native x86_64, Docker not needed.
# BUILD=local: build with Docker on this machine and push (needs Docker Desktop and good upload speed).
BUILD="${BUILD:-cloud}"
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
REPO_URI="$REGISTRY/$REPO"
IMAGE="$REPO_URI:latest"

aws ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1 \
  || { say "Creating ECR repository $REPO"; aws ecr create-repository --repository-name "$REPO" --image-scanning-configuration scanOnPush=true >/dev/null; }

if [ "$BUILD" = "local" ]; then
  command -v docker >/dev/null || die "BUILD=local needs Docker Desktop."
  docker info >/dev/null 2>&1  || die "Docker is installed but not running. Start Docker Desktop."
  say "Building backend image locally for linux/amd64"
  aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
  docker buildx build --platform linux/amd64 --target production -t "$IMAGE" --load "$ROOT/backend"
  say "Pushing image (retries up to 3 times)"
  pushed=false
  for attempt in 1 2 3; do
    if docker push "$IMAGE"; then pushed=true; break; fi
    say "Push attempt $attempt failed — retrying"; sleep 5
  done
  $pushed || die "Could not push the image. Try the default cloud build: ./deploy/aws/deploy.sh"
  docker image prune -f >/dev/null 2>&1 || true
else
  BUILD_STACK="$STACK-build"
  say "Preparing the cloud build (CodeBuild) — one-time setup takes ~1 minute"
  cfn_apply "$BUILD_STACK" "$ROOT/deploy/aws/build.yaml" RepositoryName="$REPO"
  bout() { aws cloudformation describe-stacks --stack-name "$BUILD_STACK" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
  SRC_BUCKET="$(bout SourceBucketName)"; PROJECT="$(bout ProjectName)"
  command -v zip >/dev/null || die "'zip' not found (macOS has it built in; on Linux: apt install zip)"
  TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
  say "Uploading backend source"
  ( cd "$ROOT/backend" && zip -qr "$TMPD/backend.zip" . -x ".venv/*" "*__pycache__*" ".pytest_cache/*" ".ruff_cache/*" ".env" "dev.db" "tests/*" "*.ndjson" "htmlcov/*" )
  aws s3 cp "$TMPD/backend.zip" "s3://$SRC_BUCKET/backend.zip" --only-show-errors
  if ! BUILD_ID="$(aws codebuild start-build --project-name "$PROJECT" --query build.id --output text 2>&1)"; then
    case "$BUILD_ID" in
      *"more than 0 builds"*|*"not authorized"*|*AccountLimitExceeded*)
        die "CodeBuild isn't enabled for this AWS account yet (common on new accounts): $BUILD_ID
  Workaround: BUILD=local ./deploy/aws/deploy.sh   (builds on your Mac with Docker Desktop). Or ask AWS Support to raise the CodeBuild concurrent build limit." ;;
      *) die "Could not start the image build: $BUILD_ID" ;;
    esac
  fi
  say "Building image in AWS CodeBuild (usually 2–4 minutes)"
  last=""
  while true; do
    read -r bstatus bphase <<< "$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].[buildStatus,currentPhase]' --output text)"
    if [ "$bphase" != "$last" ]; then printf "    %s\n" "$bphase"; last="$bphase"; fi
    [ "$bstatus" != "IN_PROGRESS" ] && break
    sleep 8
  done
  if [ "$bstatus" != "SUCCEEDED" ]; then
    LOGS="$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].logs.deepLink' --output text)"
    die "Image build $bstatus. Logs: $LOGS"
  fi
fi

# Keep exactly one image: delete every image except the one tagged 'latest'
OLD_UNTAGGED="$(aws ecr list-images --repository-name "$REPO" --filter tagStatus=UNTAGGED --query 'imageIds[*]' --output json)"
OLD_TAGGED="$(aws ecr list-images --repository-name "$REPO" --filter tagStatus=TAGGED --query "imageIds[?imageTag!='latest']" --output json)"
for ids in "$OLD_UNTAGGED" "$OLD_TAGGED"; do
  if [ "$ids" != "[]" ] && [ -n "$ids" ]; then
    aws ecr batch-delete-image --repository-name "$REPO" --image-ids "$ids" >/dev/null || true
  fi
done
ok "Image ready: $IMAGE (older images removed — one image kept)"

# ── 2. Infrastructure ───────────────────────────────────────────────────
VPC="$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
[ "$VPC" != "None" ] && [ -n "$VPC" ] || die "No default VPC in $REGION. Create one: aws ec2 create-default-vpc"
STATUS="$(aws cloudformation describe-stacks --stack-name "$STACK" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo NONE)"
PREV_IMAGE=""
case "$STATUS" in
  NONE|ROLLBACK_COMPLETE|ROLLBACK_FAILED|CREATE_FAILED|DELETE_FAILED|REVIEW_IN_PROGRESS)
    say "Creating stack $STACK — the database and CDN take ~15–25 minutes the first time. Grab a coffee." ;;
  *)
    PREV_IMAGE="$(aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Parameters[?ParameterKey=='ImageUri'].ParameterValue" --output text 2>/dev/null || true)"
    say "Updating stack $STACK" ;;
esac
cfn_apply "$STACK" "$ROOT/deploy/aws/template.yaml" \
  ImageUri="$IMAGE" VpcId="$VPC" TmdbApiKey="$TMDB_API_KEY" \
  BedrockModelId="$MODEL" BedrockFastModelId="$FAST" DefaultRegion="$DEFAULT_REGION"

out() { aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
WEB_URL="$(out WebUrl)"; MCP_URL="$(out McpUrl)"; BUCKET="$(out WebBucketName)"; DIST="$(out DistributionId)"; API_URL="$(out ApiServiceUrl)"
SERVICE_ARN="$(out ApiServiceArn)"
ok "Infrastructure ready"

# The image tag is always 'latest', so CloudFormation sees no change on re-runs —
# tell App Runner to pull the new image and wait for the rollout.
wait_service() {
  for _ in $(seq 1 120); do
    st="$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query Service.Status --output text)"
    [ "$st" = "RUNNING" ] && return 0
    case "$st" in *FAILED*|DELETED|PAUSED) return 1;; esac
    sleep 10
  done
  return 1
}
if [ -n "$PREV_IMAGE" ] && [ "$PREV_IMAGE" = "$IMAGE" ] && [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
  wait_service || true
  say "Rolling out the new image on App Runner (2–5 minutes, no downtime)"
  aws apprunner start-deployment --service-arn "$SERVICE_ARN" >/dev/null
  sleep 15
  if wait_service; then
    result="$(aws apprunner list-operations --service-arn "$SERVICE_ARN" --max-results 1 --query 'OperationSummaryList[0].Status' --output text)"
    if [ "$result" = "SUCCEEDED" ]; then ok "App Runner updated"; else say "App Runner rollout finished with status $result — the previous version keeps running. Check App Runner → Logs."; fi
  else
    say "App Runner is still busy — check the App Runner console"
  fi
fi

# ── 3. Web app → S3 + CloudFront ────────────────────────────────────────
say "Building the web app"
( cd "$ROOT/frontend" && npm ci --silent && VITE_API_BASE_URL='' npm run build --silent )
say "Uploading to s3://$BUCKET"
aws s3 sync "$ROOT/frontend/dist/assets" "s3://$BUCKET/assets" --delete --cache-control "public,max-age=31536000,immutable" >/dev/null
aws s3 sync "$ROOT/frontend/dist" "s3://$BUCKET" --delete --exclude "assets/*" --cache-control "no-cache" >/dev/null
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" >/dev/null
ok "Web app uploaded"

# ── 4. Smoke test ───────────────────────────────────────────────────────
say "Waiting for the API to answer through CloudFront"
for i in $(seq 1 30); do
  if curl -fsS "$WEB_URL/api/v1/health" >/dev/null 2>&1; then ok "API healthy"; break; fi
  sleep 10
  [ "$i" = 30 ] && say "API not answering yet — check App Runner logs in the AWS console (service name starts with ApiService)"
done

cat > "$ROOT/deploy/aws/outputs.env" <<OUT
WEB_URL=$WEB_URL
MCP_URL=$MCP_URL
API_URL=$API_URL
BUCKET=$BUCKET
DISTRIBUTION_ID=$DIST
IMAGE=$IMAGE
OUT

cat <<DONE

  Vibe is live.

  Web app (TV/browser):  $WEB_URL
  MCP (Alexa+):          $MCP_URL
  API docs:              $WEB_URL/api/v1/docs

  Next:
   1. Open $WEB_URL in Chrome to try it.
   2. Fire TV (Vega simulator):  ./tv-app/vega/setup.sh <your VibeTV project> $WEB_URL
   3. MCP check:                 ./scripts/mcp-smoke.sh $MCP_URL

  Saved to deploy/aws/outputs.env. Tear down after judging: ./deploy/aws/destroy.sh
DONE