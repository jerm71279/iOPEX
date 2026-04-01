#!/usr/bin/env bash
# iOPEX PAM Migration — Azure Deployment Script
# Usage: ./azure/scripts/deploy.sh <resource-group> [image-tag]
#
# Prerequisites:
#   az login
#   az account set --subscription <subscription-id>
#
# Security by Design:
#   [HIGH] Image digest captured and logged after push — immutable reference
#   [MEDIUM] Input validation on resource group name — prevent injection via $RG
#   [LOW] set -euo pipefail — fail fast on unset variables or pipe failures

set -euo pipefail

# --- Input validation [Security MEDIUM] ---
# Resource group names: 1–90 chars, alphanumerics, hyphens, underscores, periods, parens
RG=${1:?"Usage: $0 <resource-group> [image-tag]"}
if ! [[ "$RG" =~ ^[a-zA-Z0-9_\.\-\(\)]{1,90}$ ]]; then
    echo "ERROR: Invalid resource group name: '$RG'" >&2
    echo "       Allowed: letters, numbers, hyphens, underscores, periods, parens (max 90 chars)" >&2
    exit 1
fi

# Image tags: alphanumerics, hyphens, dots, underscores (no shell metacharacters)
TAG=${2:-"latest"}
if ! [[ "$TAG" =~ ^[a-zA-Z0-9_\.\-]{1,128}$ ]]; then
    echo "ERROR: Invalid image tag: '$TAG'" >&2
    echo "       Allowed: letters, numbers, hyphens, underscores, periods (max 128 chars)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_LOG="$ROOT_DIR/output/deploy_$(date +%Y%m%d_%H%M%S).log"

# Ensure output dir exists for deploy log
mkdir -p "$ROOT_DIR/output"

echo "=== iOPEX PAM Migration — Azure Deploy ===" | tee -a "$DEPLOY_LOG"
echo "Resource Group : $RG"                        | tee -a "$DEPLOY_LOG"
echo "Image Tag      : $TAG"                        | tee -a "$DEPLOY_LOG"
echo "Deploy Log     : $DEPLOY_LOG"                 | tee -a "$DEPLOY_LOG"
echo ""

# 1. Deploy infrastructure
echo "[1/4] Deploying infrastructure..." | tee -a "$DEPLOY_LOG"
az deployment group create \
  --resource-group "$RG" \
  --template-file "$ROOT_DIR/azure/bicep/main.bicep" \
  --parameters "@$ROOT_DIR/azure/bicep/parameters.json" \
  --parameters imageTag="$TAG" \
  --output table 2>&1 | tee -a "$DEPLOY_LOG"

# 2. Get ACR login server
ACR=$(az deployment group show \
  --resource-group "$RG" \
  --name main \
  --query properties.outputs.acrLoginServer.value \
  --output tsv)

echo "" | tee -a "$DEPLOY_LOG"
echo "[2/4] Building and pushing container image to $ACR..." | tee -a "$DEPLOY_LOG"

az acr login --name "${ACR%%.*}" 2>&1 | tee -a "$DEPLOY_LOG"

# Build with full tag
docker build -t "$ACR/pam-migration:$TAG" "$ROOT_DIR" 2>&1 | tee -a "$DEPLOY_LOG"
docker push "$ACR/pam-migration:$TAG" 2>&1 | tee -a "$DEPLOY_LOG"

# Capture image digest — Security [HIGH]: immutable reference for audit trail
# Digest pins the exact image layer that was pushed; tags are mutable, digests are not
IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$ACR/pam-migration:$TAG" 2>/dev/null || echo "digest-unavailable")
echo ""                                                                          | tee -a "$DEPLOY_LOG"
echo "Image digest   : $IMAGE_DIGEST"                                            | tee -a "$DEPLOY_LOG"
echo "  Security [HIGH]: Record this digest in your change management ticket."   | tee -a "$DEPLOY_LOG"
echo "  Use digest reference in production: $ACR/pam-migration@${IMAGE_DIGEST##*@}" | tee -a "$DEPLOY_LOG"

# 3. Update Container App to use pinned digest (if available)
echo "" | tee -a "$DEPLOY_LOG"
echo "[3/4] Verifying deployment..." | tee -a "$DEPLOY_LOG"
APP=$(az deployment group show \
  --resource-group "$RG" \
  --name main \
  --query properties.outputs.containerAppName.value \
  --output tsv)

az containerapp show --name "$APP" --resource-group "$RG" --output table 2>&1 | tee -a "$DEPLOY_LOG"

# 4. Run preflight to confirm system health
echo "" | tee -a "$DEPLOY_LOG"
echo "[4/4] Running preflight check..." | tee -a "$DEPLOY_LOG"
az containerapp exec \
  --name "$APP" \
  --resource-group "$RG" \
  --command "python3 cli.py preflight" 2>&1 | tee -a "$DEPLOY_LOG"

# Get dashboard URL and wire into Container App env
DASHBOARD_URL=$(az deployment group show \
  --resource-group "$RG" \
  --name main \
  --query properties.outputs.dashboardUrl.value \
  --output tsv 2>/dev/null || echo "")

if [ -n "$DASHBOARD_URL" ]; then
    echo "" | tee -a "$DEPLOY_LOG"
    echo "Wiring dashboard URL into Container App..." | tee -a "$DEPLOY_LOG"
    az containerapp update --name "$APP" --resource-group "$RG" \
      --set-env-vars "DASHBOARD_STORAGE_URL=${DASHBOARD_URL%dashboard/status.json}" \
      2>&1 | tee -a "$DEPLOY_LOG"
fi

echo ""                                                                            | tee -a "$DEPLOY_LOG"
echo "=== Deploy complete ==="                                                     | tee -a "$DEPLOY_LOG"
echo "Image digest   : $IMAGE_DIGEST"                                              | tee -a "$DEPLOY_LOG"
echo "Deploy log     : $DEPLOY_LOG"                                                | tee -a "$DEPLOY_LOG"
if [ -n "$DASHBOARD_URL" ]; then
    echo "Dashboard URL  : $DASHBOARD_URL"                                         | tee -a "$DEPLOY_LOG"
    echo "  → Share this URL with iOPEX team and Cisco stakeholders"               | tee -a "$DEPLOY_LOG"
    echo "  → Set this in the Control Center: window.DASHBOARD_CONFIG.blobUrl"     | tee -a "$DEPLOY_LOG"
fi
echo "Run migration  : az containerapp exec --name $APP --resource-group $RG --command 'python3 cli.py run P1'" | tee -a "$DEPLOY_LOG"
