#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy NOC Agentic AI to AWS ECS
set -euo pipefail

# ── Config (override via env vars) ────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-me-south-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_BACKEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/noc-backend"
ECR_FRONTEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/noc-frontend"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NOC Agentic AI — AWS Deployment"
echo "  Region: $AWS_REGION | Account: $AWS_ACCOUNT_ID | Tag: $IMAGE_TAG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. ECR Login ──────────────────────────────────────────────────────────────
echo "[1/5] Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# ── 2. Build images ───────────────────────────────────────────────────────────
echo "[2/5] Building Docker images..."
docker build -t noc-backend:$IMAGE_TAG ./backend
docker build -t noc-frontend:$IMAGE_TAG ./frontend

# ── 3. Tag & Push ─────────────────────────────────────────────────────────────
echo "[3/5] Pushing to ECR..."
docker tag noc-backend:$IMAGE_TAG $ECR_BACKEND:$IMAGE_TAG
docker tag noc-backend:$IMAGE_TAG $ECR_BACKEND:latest
docker push $ECR_BACKEND:$IMAGE_TAG
docker push $ECR_BACKEND:latest

docker tag noc-frontend:$IMAGE_TAG $ECR_FRONTEND:$IMAGE_TAG
docker tag noc-frontend:$IMAGE_TAG $ECR_FRONTEND:latest
docker push $ECR_FRONTEND:$IMAGE_TAG
docker push $ECR_FRONTEND:latest

# ── 4. CDK Deploy ─────────────────────────────────────────────────────────────
echo "[4/5] Deploying infrastructure with CDK..."
cd infrastructure/cdk
npm install --silent
npm run build
npx cdk deploy --all --require-approval never --outputs-file ../../cdk-outputs.json
cd ../..

# ── 5. Force ECS service update ───────────────────────────────────────────────
echo "[5/5] Forcing ECS service update..."
aws ecs update-service \
  --cluster noc-cluster \
  --service BackendService \
  --force-new-deployment \
  --region "$AWS_REGION" > /dev/null

aws ecs update-service \
  --cluster noc-cluster \
  --service FrontendService \
  --force-new-deployment \
  --region "$AWS_REGION" > /dev/null

# ── Output URL ────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Deployment complete!"
if [ -f cdk-outputs.json ]; then
  URL=$(cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0].get('LoadBalancerUrl',''))" 2>/dev/null || echo "Check AWS Console")
  echo "  🌐  URL: $URL"
fi
echo "  📊  ECS Console: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
