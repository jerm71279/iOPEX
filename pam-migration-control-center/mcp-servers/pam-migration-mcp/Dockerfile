FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY . /app/pam_migration_mcp/

# Create output directories
RUN mkdir -p /app/output/state /app/output/logs /app/output/state/raw

ENV PAM_MCP_HOST=0.0.0.0
ENV PAM_MCP_PORT=8100
ENV PAM_MCP_OUTPUT_DIR=/app/output
ENV PAM_MCP_STATE_DIR=/app/output/state
ENV PAM_MCP_LOG_DIR=/app/output/logs
ENV PAM_MCP_FROZEN_REGISTRY_PATH=/app/output/state/frozen_accounts.json

EXPOSE 8100

CMD ["python", "-m", "pam_migration_mcp.server"]
