"""
iOPEX MCP Hub — intelligence aggregation point for Claude Code + OpenClaw.

Serves MCP-over-SSE on port 8002 (host-mapped to 8010).
Mounts three tool groups:
  /mcp/shift      — SHIFT PAM Control Center tools
  /mcp/iopex      — iOPEX Digital Expert query tools
  /mcp/pam-status — KeeperPAM + gate status tools

Usage in Claude Code .mcp.json:
  {
    "mcpServers": {
      "shift":      { "url": "http://localhost:8010/mcp/shift/sse" },
      "iopex":      { "url": "http://localhost:8010/mcp/iopex/sse" },
      "pam-status": { "url": "http://localhost:8010/mcp/pam-status/sse" }
    }
  }
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from tools.shift_tools import mcp as shift_mcp
from tools.iopex_tools import mcp as iopex_mcp
from tools.pam_tools import mcp as pam_mcp

# ---------------------------------------------------------------------------
# Root FastAPI app — health only; MCP routes mounted below
# ---------------------------------------------------------------------------
app = FastAPI(title="iOPEX MCP Hub", version="1.0.0")


@app.get("/health")
def health():
    return {
        "status":   "ok",
        "service":  "iOPEX MCP Hub",
        "version":  "1.0.0",
        "routes":   ["/mcp/shift", "/mcp/iopex", "/mcp/pam-status"],
        "host":     "http://localhost:8010",
        "shift_api": os.environ.get("SHIFT_API_URL", "http://localhost:8000"),
        "iopex_api": os.environ.get("IOPEX_API_URL", "http://localhost:8001"),
    }


# ---------------------------------------------------------------------------
# Mount FastMCP sub-apps — each handles /sse, /messages, etc. internally
# ---------------------------------------------------------------------------
app.mount("/mcp/shift",      shift_mcp.http_app())
app.mount("/mcp/iopex",      iopex_mcp.http_app())
app.mount("/mcp/pam-status", pam_mcp.http_app())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
