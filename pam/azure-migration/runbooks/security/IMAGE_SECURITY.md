# Container Image Security
## CyberArk → KeeperPAM Migration | SHIFT System

**Document ID:** SEC-IMG-001
**Last Updated:** 2026-03-30
**Owner:** DevOps Lead
**Applies To:** Docker image build, push, and deployment lifecycle for the SHIFT migration system

---

## Image Build Security Checklist

Complete before every production build:

- [ ] `.dockerignore` is present and excludes `config.json`, `.env`, `output/`, `*.key`, `*.pem`
- [ ] Base image is pinned to a specific digest (not `:latest`)
- [ ] No build arguments contain credentials or secrets
- [ ] `pip install` uses hashed `requirements.txt` (see supply chain section)
- [ ] No `curl`, `wget`, or unnecessary network tools in the final image
- [ ] `HEALTHCHECK` instruction present in Dockerfile
- [ ] Image built with `--no-cache` for weekly base image refresh builds
- [ ] Local Trivy scan completed with zero CRITICAL findings before push (see scan section)
- [ ] Image digest captured after push (see digest pinning section)
- [ ] Container App updated to reference digest, not tag

---

## ACR Vulnerability Scanning

### Enable Microsoft Defender for Containers

Microsoft Defender for Containers provides automatic vulnerability assessment for images pushed to Azure Container Registry. It is part of Microsoft Defender for Cloud.

```bash
# Enable Defender for Containers on the subscription
az security pricing create \
  --name Containers \
  --tier Standard

# Enable on a specific ACR (if not subscription-wide)
az security setting update \
  --name MCAS \
  --enabled true
```

> **Note:** Microsoft Defender for Containers is billed per vCore of AKS nodes and per 1,000 images scanned per month. For a Container Apps workload, billing is per image pushed to ACR. Check current pricing at https://azure.microsoft.com/pricing/details/defender-for-cloud/.

### View Scan Results in Microsoft Defender for Cloud

1. Open **Microsoft Defender for Cloud** in the Azure Portal.
2. Navigate to **Recommendations**.
3. Filter by resource type: **Container Registry**.
4. Find: *"Container registry images should have vulnerability findings resolved"*
5. Expand to see per-image CVE findings with severity and fix versions.

### View via Azure Security Center CLI

```bash
# List security assessments for the ACR resource
az security assessment list \
  --resource-group <rg-name> \
  --query "[?contains(id, 'containerRegistry')]" \
  --output table
```

---

## ACR Quarantine Policy

ACR Quarantine Policy holds newly pushed images until a vulnerability scan completes and passes. Requires **Premium SKU**.

> **Premium SKU Note:** The quarantine policy feature requires ACR Premium tier (~$0.667/day). If the deployment uses Basic or Standard SKU, quarantine is not available. Use Trivy in the CI/CD pipeline as the pre-push gate instead.

```bash
# Enable quarantine policy (Premium SKU required)
az acr config content-trust update \
  --name <acr-name> \
  --status enabled

# Enable quarantine feature flag
az acr update \
  --name <acr-name> \
  --quarantine enabled
```

When quarantine is enabled, images are tagged `Quarantined` on push and only promoted to `OK` state after scan passes. Container Apps configured to use `Quarantined` images will fail to pull until the scan completes.

---

## Trivy Local Scan

Trivy is an open-source vulnerability scanner for container images. Run before every push to ACR.

### Installation

```bash
# Linux/WSL
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Or via apt
sudo apt-get install -y wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy
```

### Scan Command

```bash
# Scan local image before push — fail on CRITICAL findings
trivy image --exit-code 1 --severity CRITICAL <image-name>:<tag>

# Full scan including HIGH (recommended for pre-production)
trivy image --exit-code 1 --severity CRITICAL,HIGH <image-name>:<tag>

# Output as JSON for CI/CD artifact
trivy image --format json --output trivy-report.json <image-name>:<tag>

# Scan with SBOM (software bill of materials) output
trivy image --format cyclonedx --output sbom.json <image-name>:<tag>
```

**Acceptable Thresholds:**

| Finding Severity | Threshold |
|-----------------|-----------|
| CRITICAL | Zero tolerance — must fix before push |
| HIGH | Resolve before P5 (production); document exception if OS vendor has not released fix |
| MEDIUM/LOW | Track and resolve in next base image refresh cycle |

---

## Image Digest Pinning

Using a mutable tag (e.g., `:v1.2.3`) allows the tag to be overwritten in ACR, creating an image substitution risk. Pin Container App to the immutable digest instead.

### Capture Digest After Push

```bash
# Push image
docker build -t <acr-login-server>/<image-name>:<tag> .
docker push <acr-login-server>/<image-name>:<tag>

# Capture digest immediately after push
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' <acr-login-server>/<image-name>:<tag>)
echo "Image digest: $DIGEST"
# Example output: shift.azurecr.io/shift-migration:v1.2.3@sha256:a1b2c3d4...
```

### Update Container App to Use Digest

```bash
# Update Container App to reference the immutable digest
az containerapp update \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --image "${DIGEST}"

# Verify
az containerapp show \
  --name shift-migration-app \
  --resource-group <rg-name> \
  --query "properties.template.containers[0].image" \
  --output tsv
# Expected: shift.azurecr.io/shift-migration:v1.2.3@sha256:a1b2c3...
```

### deploy.sh Integration

The SHIFT `deploy.sh` script captures the digest automatically:

```bash
# In deploy.sh (post-push section)
docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${TAG}"
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${TAG}")
echo "[INFO] Image digest: ${DIGEST}"
az containerapp update \
  --name "${APP_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${DIGEST}"
```

---

## Base Image Update Policy

| Environment | Policy |
|-------------|--------|
| Development | Pull latest base image weekly; rebuild with `--no-cache` |
| Pre-production / staging | Pin to specific digest; rebuild and re-test before promoting to production |
| Production | Pin to digest; update only after Trivy scan passes on new base image |

### Weekly Base Image Refresh

```bash
# Force pull of updated base image
docker pull python:3.12-slim

# Capture new base image digest
BASE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim)
echo "New base image digest: ${BASE_DIGEST}"

# Update Dockerfile (first line)
# FROM python:3.12-slim@sha256:<new-digest>

# Rebuild and scan
docker build --no-cache -t <acr-login-server>/<image-name>:latest .
trivy image --exit-code 1 --severity CRITICAL,HIGH <acr-login-server>/<image-name>:latest
```

---

## ACR Geo-Replication

ACR Geo-Replication replicates the registry to multiple Azure regions for high availability and reduced pull latency. Requires **Premium SKU**.

> **Premium SKU Note:** Geo-replication requires ACR Premium tier. Each replica costs approximately $0.667/day per region.

```bash
# Add a replica to a secondary region (Premium SKU required)
az acr replication create \
  --registry <acr-name> \
  --location eastus2

# List replicas
az acr replication list \
  --registry <acr-name> \
  --output table
```

For the SHIFT migration system (single-region deployment), geo-replication is not required. It is relevant only if the client requires disaster recovery or multi-region failover of the migration platform itself.

---

## Supply Chain Protection — Dependency Pinning

All pip packages must be pinned to specific versions with cryptographic hashes in `requirements.txt`. This prevents dependency confusion attacks and ensures reproducible builds.

### Workflow

**Step 1 — Maintain a high-level `requirements.in`**

```
# requirements.in
requests>=2.31.0
urllib3>=2.0.0
python-docx>=1.1.0
pyodbc>=5.0.0
opencensus-ext-azure>=1.1.0
```

**Step 2 — Compile to `requirements.txt` with hashes**

```bash
# Install pip-tools
pip install pip-tools

# Compile with hash generation
pip-compile --generate-hashes requirements.in > requirements.txt
```

This produces entries like:

```
requests==2.31.0 \
    --hash=sha256:58cd2187423d... \
    --hash=sha256:942c5a758f98...
```

**Step 3 — Use hashed requirements in Dockerfile**

```dockerfile
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
```

The `--require-hashes` flag causes pip to reject any package whose hash does not match. Packages installed without a hash in `requirements.txt` will cause the build to fail.

**Step 4 — Refresh monthly**

```bash
# Update all packages to latest compatible versions and regenerate hashes
pip-compile --generate-hashes --upgrade requirements.in > requirements.txt
```

---

## CI/CD Pipeline Integration

### GitHub Actions (automated scan on push)

```yaml
# .github/workflows/image-security.yml
name: Container Image Security Scan

on:
  push:
    branches: [main, feature/**]
  pull_request:
    branches: [main]

jobs:
  trivy-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t shift-migration:${{ github.sha }} .

      - name: Run Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: shift-migration:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1

      - name: Upload Trivy scan results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      - name: Push to ACR (on main branch only)
        if: github.ref == 'refs/heads/main'
        run: |
          az acr login --name ${{ secrets.ACR_NAME }}
          docker tag shift-migration:${{ github.sha }} ${{ secrets.ACR_LOGIN_SERVER }}/shift-migration:${{ github.sha }}
          docker push ${{ secrets.ACR_LOGIN_SERVER }}/shift-migration:${{ github.sha }}
          DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ${{ secrets.ACR_LOGIN_SERVER }}/shift-migration:${{ github.sha }})
          echo "IMAGE_DIGEST=${DIGEST}" >> $GITHUB_ENV
          echo "Image digest: ${DIGEST}"
```

### Azure DevOps Pipeline

```yaml
# azure-pipelines-image-security.yml
trigger:
  branches:
    include: [main]

pool:
  vmImage: ubuntu-latest

steps:
  - script: |
      curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    displayName: Install Trivy

  - script: docker build -t shift-migration:$(Build.BuildId) .
    displayName: Build container image

  - script: |
      trivy image --exit-code 1 --severity CRITICAL,HIGH \
        --format template --template "@contrib/junit.tpl" \
        -o trivy-junit.xml \
        shift-migration:$(Build.BuildId)
    displayName: Trivy vulnerability scan

  - task: PublishTestResults@2
    inputs:
      testResultsFormat: JUnit
      testResultsFiles: trivy-junit.xml
    displayName: Publish scan results
    condition: always()

  - script: |
      az acr login --name $(ACR_NAME)
      docker tag shift-migration:$(Build.BuildId) $(ACR_LOGIN_SERVER)/shift-migration:$(Build.BuildId)
      docker push $(ACR_LOGIN_SERVER)/shift-migration:$(Build.BuildId)
      DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $(ACR_LOGIN_SERVER)/shift-migration:$(Build.BuildId))
      echo "##vso[task.setvariable variable=IMAGE_DIGEST]${DIGEST}"
    displayName: Push to ACR
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
```

---

*End of Container Image Security*
