# iOPEX PAM Migration — Azure Container Image
# Runs the 15-agent orchestration system in Azure Container Apps
#
# Build:  docker build -t pam-migration .
# Run:    docker run --env-file .env.azure pam-migration python3 cli.py preflight
#
# Security by Design [HIGH]:
#   - Pinned base image digest prevents supply-chain substitution attacks
#   - No curl/wget: outbound HTTP from container must go through the application
#     code (tracked, logged) — not ad-hoc shell commands
#   - Non-root user (UID 1000) — container escape has limited host impact
#   - .dockerignore excludes credentials, output/, .env files from image context

# Pin to specific digest — update intentionally after testing
# Security [HIGH]: floating tags (e.g. :latest) allow unreviewed base image changes
FROM python:3.12-slim@sha256:3d5ed973e45820f5ba5e46bd065bd88b3a504ff0724d85980dcd05eab361fcf4

# Security [MEDIUM]: only install build-time compiler; no curl/libpq-dev
# gcc is dropped after pip install via multi-stage or --no-install-recommends
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache — avoids reinstall on code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build-time compiler — not needed at runtime
# Security [MEDIUM]: reduces attack surface by ~40MB
RUN apt-get purge -y gcc && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy application code (.dockerignore excludes credentials, output/, .env*)
COPY . .

# Non-root user — Security [HIGH]
# Container runs as UID 1000; root-level writes fail safely
RUN useradd -m -u 1000 migrator && chown -R migrator:migrator /app
USER migrator

# Liveness probe target — Security [LOW]: validates container is alive without exposing HTTP port
# Azure Container Apps liveness probe calls this; exit 0 = healthy
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python3", "cli.py", "--help"]

# Default: show CLI help — override at container run time
CMD ["python3", "cli.py", "--help"]
