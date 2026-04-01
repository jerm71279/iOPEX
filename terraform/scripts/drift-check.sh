#!/usr/bin/env bash
# ─── drift-check.sh ──────────────────────────────────────────────────────────
# P6 Parallel Running — Infrastructure Drift Detection
#
# Runs `terraform plan -detailed-exitcode` against the specified composition.
# Exit codes:
#   0 = No changes (no drift)
#   1 = Error
#   2 = Drift detected (changes required)
#
# Designed to run on a schedule (cron or GitHub Actions) during Phase 6
# parallel running to detect infrastructure configuration drift.
#
# Usage:
#   ./scripts/drift-check.sh shared dev
#   ./scripts/drift-check.sh option-a staging
#   ./scripts/drift-check.sh option-b prod
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

COMPOSITION="${1:?Usage: drift-check.sh <composition> <environment>}"
ENVIRONMENT="${2:?Usage: drift-check.sh <composition> <environment>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSITION_DIR="${SCRIPT_DIR}/../compositions/${COMPOSITION}"

if [ ! -d "${COMPOSITION_DIR}" ]; then
  echo "ERROR: Composition directory not found: ${COMPOSITION_DIR}"
  exit 1
fi

echo "=== PAM Migration — Drift Check ==="
echo "Composition: ${COMPOSITION}"
echo "Environment: ${ENVIRONMENT}"
echo "Timestamp:   $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

cd "${COMPOSITION_DIR}"

# Initialize (in case .terraform is not present)
terraform init \
  -backend-config="key=${COMPOSITION}.${ENVIRONMENT}.tfstate" \
  -input=false \
  -no-color \
  2>&1 | tail -1

echo ""
echo "--- Running drift detection ---"
echo ""

# Plan with detailed exit code
EXIT_CODE=0
terraform plan \
  -var-file="../../environments/${ENVIRONMENT}.tfvars" \
  -detailed-exitcode \
  -input=false \
  -no-color \
  2>&1 || EXIT_CODE=$?

echo ""
echo "--- Result ---"

case ${EXIT_CODE} in
  0)
    echo "NO DRIFT DETECTED — infrastructure matches Terraform state"
    ;;
  1)
    echo "ERROR — terraform plan failed (check provider credentials and connectivity)"
    ;;
  2)
    echo "DRIFT DETECTED — infrastructure has changed outside of Terraform"
    echo ""
    echo "Action required:"
    echo "  1. Review the plan output above"
    echo "  2. If drift is intentional, run: terraform apply -var-file=../../environments/${ENVIRONMENT}.tfvars"
    echo "  3. If drift is unauthorized, investigate and remediate"
    echo "  4. Notify the migration team (Agent 15 — Hybrid Fleet Manager)"
    ;;
esac

exit ${EXIT_CODE}
