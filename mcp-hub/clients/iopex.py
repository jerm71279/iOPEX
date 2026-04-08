"""
Async HTTP client for the iOPEX Digital Expert API (jit-iopex-agent:8001).
"""
import os
import httpx

IOPEX_URL = os.environ.get("IOPEX_API_URL", "http://localhost:8001")
TIMEOUT = 30.0


async def health() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{IOPEX_URL}/health")
        r.raise_for_status()
        return r.json()


async def query(question: str, client_id: str = "mcp-hub", domain: str = None) -> dict:
    payload = {"query": question, "client_id": client_id}
    if domain:
        payload["domain"] = domain
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(f"{IOPEX_URL}/query", json=payload)
        r.raise_for_status()
        return r.json()
