FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY . /app/control_center_mcp/

ENV CC_MCP_HOST=0.0.0.0
ENV CC_MCP_PORT=8101
ENV CC_MCP_CONTROL_CENTER_URL=http://control-center:8080

EXPOSE 8101

CMD ["python", "-m", "control_center_mcp.server"]
