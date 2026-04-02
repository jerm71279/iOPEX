#!/usr/bin/env bash
# upload-nexus-wheel.sh — Build nexus-core wheel and upload to Azure Blob Storage
#
# Run this BEFORE `terraform apply` so the wheel is available when cloud-init
# executes on the VM's first boot.
#
# Prerequisites:
#   - az login (or managed identity)
#   - Python 3.12 + pip + build: pip install build
#   - The nexus-core repo at ~/projects/nexus-core (or NEXUS_CORE_DIR override)
#
# Usage:
#   ./scripts/upload-nexus-wheel.sh
#   NEXUS_WHEEL_STORAGE_ACCOUNT=mystorageacct ./scripts/upload-nexus-wheel.sh
#   NEXUS_CORE_DIR=/path/to/nexus-core ./scripts/upload-nexus-wheel.sh

set -euo pipefail

# ── Configuration (override via env vars) ─────────────────────────────────────
NEXUS_CORE_DIR="${NEXUS_CORE_DIR:-$HOME/projects/nexus-core}"
STORAGE_ACCOUNT="${NEXUS_WHEEL_STORAGE_ACCOUNT:-stpamtfstate}"
CONTAINER="nexus-core-packages"
DIST_DIR="$NEXUS_CORE_DIR/dist"

echo "=== nexus-core wheel build + upload ==="
echo "Source:          $NEXUS_CORE_DIR"
echo "Storage account: $STORAGE_ACCOUNT"
echo "Container:       $CONTAINER"
echo ""

# ── Validate prerequisites ────────────────────────────────────────────────────
if [ ! -d "$NEXUS_CORE_DIR" ]; then
  echo "ERROR: nexus-core directory not found: $NEXUS_CORE_DIR"
  echo "       Set NEXUS_CORE_DIR to override."
  exit 1
fi

if ! command -v az &> /dev/null; then
  echo "ERROR: Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

if ! python3 -c "import build" &> /dev/null; then
  echo "INFO: Installing build package..."
  pip install --quiet build
fi

# ── Build wheel ───────────────────────────────────────────────────────────────
echo "[1/4] Building nexus-core wheel..."
rm -rf "$DIST_DIR"
(cd "$NEXUS_CORE_DIR" && python3 -m build --wheel --outdir dist/)

WHEEL_FILE=$(ls "$DIST_DIR"/nexus_core-*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL_FILE" ]; then
  echo "ERROR: No wheel found in $DIST_DIR after build."
  exit 1
fi

WHEEL_NAME=$(basename "$WHEEL_FILE")
echo "  Built: $WHEEL_NAME"

# ── Ensure blob container exists ──────────────────────────────────────────────
echo "[2/4] Ensuring blob container exists: $CONTAINER"
az storage container create \
  --name "$CONTAINER" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --output none 2>/dev/null || true

# ── Upload wheel ──────────────────────────────────────────────────────────────
echo "[3/4] Uploading $WHEEL_NAME to $STORAGE_ACCOUNT/$CONTAINER..."
az storage blob upload \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --file "$WHEEL_FILE" \
  --name "$WHEEL_NAME" \
  --overwrite true \
  --auth-mode login \
  --output none

# ── Verify ────────────────────────────────────────────────────────────────────
echo "[4/4] Verifying upload..."
UPLOADED=$(az storage blob show \
  --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --name "$WHEEL_NAME" \
  --auth-mode login \
  --query "properties.contentLength" \
  --output tsv 2>/dev/null || echo "0")

echo ""
echo "=== Upload complete ==="
echo "Wheel:    $WHEEL_NAME"
echo "Size:     ${UPLOADED} bytes"
echo "Blob URL: https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER}/${WHEEL_NAME}"
echo ""
echo "Next: terraform apply -var-file=environments/dev.tfvars"
echo "      Ensure nexus_wheel_version in dev.tfvars matches: $(echo "$WHEEL_NAME" | grep -oP '(?<=nexus_core-)[^-]+')"
