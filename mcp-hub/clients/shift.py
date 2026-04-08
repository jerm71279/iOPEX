"""
Async HTTP client for the SHIFT Agent API (jit-shift-api:8000).
All methods return plain dicts — tool layer handles formatting.
"""
import os
import httpx

SHIFT_URL = os.environ.get("SHIFT_API_URL", "http://localhost:8000")
TIMEOUT = 30.0


async def health() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{SHIFT_URL}/health")
        r.raise_for_status()
        return r.json()


async def wave_status() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{SHIFT_URL}/wave/status")
        r.raise_for_status()
        return r.json()


async def agent_status() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"{SHIFT_URL}/agents/status")
        r.raise_for_status()
        return r.json()


async def ask(question: str, context: str = "") -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(f"{SHIFT_URL}/ask", json={"question": question, "context": context})
        r.raise_for_status()
        return r.json()
