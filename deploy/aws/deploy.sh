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
[ -n "$TMDB_API_KEY" ] && [ "$TMDB_API_KEY" != "your_tmdb_api_key" ] || die "TMDB_API_KEY missing (set it in backend/.env)"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" || die "AWS credentials not working. Run 'aws configure' or set keys in backend/.env"
ok "AWS account $ACCOUNT, region $REGION, stack $STACK"

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
  aws cloudformation deploy --stack-name "$BUILD_STACK" --template-file "$ROOT/deploy/aws/build.yaml" \
    --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset --parameter-overrides RepositoryName="$REPO" >/dev/null
  bout() { aws cloudformation describe-stacks --stack-name "$BUILD_STACK" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
  SRC_BUCKET="$(bout SourceBucketName)"; PROJECT="$(bout ProjectName)"
  command -v zip >/dev/null || die "'zip' not found (macOS has it built in; on Linux: apt install zip)"
  TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
  say "Uploading backend source"
  ( cd "$ROOT/backend" && zip -qr "$TMPD/backend.zip" . -x ".venv/*" "*__pycache__*" ".pytest_cache/*" ".ruff_cache/*" ".env" "dev.db" "tests/*" "*.ndjson" "htmlcov/*" )
  aws s3 cp "$TMPD/backend.zip" "s3://$SRC_BUCKET/backend.zip" --only-show-errors
  BUILD_ID="$(aws codebuild start-build --project-name "$PROJECT" --query build.id --output text)"
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
STATUS="$(aws cloudformation describe-stacks --stack-name "$STACK" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
if [ "$STATUS" = "ROLLBACK_COMPLETE" ]; then
  say "A previous first-time deploy failed (ROLLBACK_COMPLETE). Removing it before retrying"
  aws cloudformation delete-stack --stack-name "$STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK"
fi
PREV_IMAGE="$(aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Parameters[?ParameterKey=='ImageUri'].ParameterValue" --output text 2>/dev/null || true)"
if ! aws cloudformation describe-stacks --stack-name "$STACK" >/dev/null 2>&1; then
  PREV_IMAGE=""
  say "Creating stack $STACK — the database takes ~10–15 minutes the first time. Grab a coffee."
else
  say "Updating stack $STACK (App Runner rolls out the new image)"
fi
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$ROOT/deploy/aws/template.yaml" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
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
