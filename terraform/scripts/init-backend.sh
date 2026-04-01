#!/usr/bin/env bash
# ─── init-backend.sh ──────────────────────────────────────────────────────────
# Creates the Azure Storage account for Terraform remote state.
# Run ONCE before the first `terraform init`.
#
# Prerequisites:
#   - Azure CLI installed and authenticated (`az login`)
#   - Sufficient permissions to create resource groups and storage accounts
#
# Usage:
#   chmod +x scripts/init-backend.sh
#   ./scripts/init-backend.sh
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

RESOURCE_GROUP="rg-pam-tfstate"
STORAGE_ACCOUNT="stpamtfstate"
CONTAINER="tfstate"
LOCATION="eastus2"

echo "=== PAM Migration — Terraform State Backend Setup ==="
echo ""

# 1. Resource group
echo "[1/4] Creating resource group: ${RESOURCE_GROUP}"
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --tags project=pam-migration managed_by=terraform purpose=tfstate \
  --output none

# 2. Storage account (LRS, TLS 1.2, blob encryption)
echo "[2/4] Creating storage account: ${STORAGE_ACCOUNT}"
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --encryption-services blob \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --tags project=pam-migration managed_by=terraform purpose=tfstate \
  --output none

# 3. Blob container
echo "[3/4] Creating blob container: ${CONTAINER}"
az storage container create \
  --name "${CONTAINER}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --auth-mode login \
  --output none

# 4. Enable versioning for state file recovery
echo "[4/4] Enabling blob versioning"
az storage account blob-service-properties update \
  --account-name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --enable-versioning true \
  --output none

echo ""
echo "=== Backend ready ==="
echo "Resource Group:  ${RESOURCE_GROUP}"
echo "Storage Account: ${STORAGE_ACCOUNT}"
echo "Container:       ${CONTAINER}"
echo ""
echo "Initialize compositions with:"
echo "  cd compositions/shared"
echo "  terraform init -backend-config=\"key=shared.dev.tfstate\""
echo ""
echo "  cd compositions/option-a"
echo "  terraform init -backend-config=\"key=option-a.dev.tfstate\""
