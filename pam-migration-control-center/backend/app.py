"""
PAM Migration Control Center — FastAPI Application
Serves the frontend SPA and REST API with mock/importable data.
"""
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routers import dashboard, phases, agents, waves, gates, deliverables, accounts, checkpoints, mcp, ml
from backend.routers import state as state_router
from backend.routers import integrity, circuit_breaker, schema_drift
from backend.routers import pmo as pmo_router
from backend.mock_data import PHASES, AGENTS, WAVES, GATES, OPTIONS, DELIVERABLES

app = FastAPI(
    title="PAM Migration Control Center",
    version="1.0.0",
    description="Interactive control center for PAM migration journey (Cisco: Devolutions 44w / Keeper 36w / MiniOrange 32w)",
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DATA_DIR = Path(__file__).parent / "imported_data"
DATA_DIR.mkdir(exist_ok=True)

# ── API Routers ──────────────────────────────────────────────────────
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(phases.router, prefix="/api/phases", tags=["Phases"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(waves.router, prefix="/api/waves", tags=["Waves"])
app.include_router(gates.router, prefix="/api/gates", tags=["Gates"])
app.include_router(deliverables.router, prefix="/api/deliverables", tags=["Deliverables"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(checkpoints.router, prefix="/api/checkpoints", tags=["Checkpoints"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP"])
app.include_router(ml.router, prefix="/api/ml", tags=["ML"])
app.include_router(state_router.router, prefix="/api/state", tags=["State"])
app.include_router(integrity.router, prefix="/api/integrity", tags=["Integrity"])
app.include_router(circuit_breaker.router, prefix="/api/circuit-breaker", tags=["Circuit Breaker"])
app.include_router(schema_drift.router, prefix="/api/schema-drift", tags=["Schema Drift"])
app.include_router(pmo_router.router, prefix="/api/pmo", tags=["PMO Intelligence"])


# ── Data Import Endpoint ─────────────────────────────────────────────
@app.post("/api/import/{data_type}", tags=["Import"])
async def import_data(data_type: str, file: UploadFile = File(...)):
    """
    Import custom mock/test data. Accepts JSON files.
    data_type: one of 'phases', 'agents', 'waves', 'gates', 'deliverables'
    The imported data overrides mock data until server restart.
    """
    allowed = {"phases", "agents", "waves", "gates", "deliverables", "discovery", "heartbeat", "staging"}
    if data_type not in allowed:
        raise HTTPException(400, f"Invalid data_type. Allowed: {', '.join(sorted(allowed))}")
    if not file.filename.endswith(".json"):
        raise HTTPException(400, "Only .json files are accepted")
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    out_path = DATA_DIR / f"{data_type}.json"
    out_path.write_text(json.dumps(data, indent=2))
    # Update in-memory data
    _apply_import(data_type, data)
    return {"status": "imported", "data_type": data_type, "records": len(data) if isinstance(data, (list, dict)) else 1}


@app.get("/api/import/status", tags=["Import"])
async def import_status():
    """List all imported data files."""
    files = [f.name for f in DATA_DIR.glob("*.json")]
    return {"imported_files": files, "data_dir": str(DATA_DIR)}


@app.delete("/api/import/{data_type}", tags=["Import"])
async def clear_import(data_type: str):
    """Remove imported data and revert to mock data."""
    path = DATA_DIR / f"{data_type}.json"
    if path.exists():
        path.unlink()
    return {"status": "cleared", "data_type": data_type, "reverted_to": "mock_data"}


def _apply_import(data_type: str, data):
    """Apply imported data to the in-memory data stores used by routers."""
    import backend.mock_data.data as store
    if data_type == "phases" and isinstance(data, dict):
        store.PHASES.update(data)
    elif data_type == "agents" and isinstance(data, dict):
        store.AGENTS.update(data)
    elif data_type == "waves" and isinstance(data, dict):
        store.WAVES.update(data)
    elif data_type == "gates" and isinstance(data, list):
        store.GATES.clear()
        store.GATES.extend(data)
    elif data_type == "deliverables" and isinstance(data, dict):
        store.DELIVERABLES.update(data)


def _load_imports_on_startup():
    """Load any previously imported data files on startup."""
    for f in DATA_DIR.glob("*.json"):
        data_type = f.stem
        try:
            data = json.loads(f.read_text())
            _apply_import(data_type, data)
        except Exception:
            pass


_load_imports_on_startup()

# ── Static Files (frontend) ─────────────────────────────────────────
DOCS_DIR = Path(__file__).parent.parent / "docs"
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
if DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(DOCS_DIR), html=True), name="docs")


@app.get("/life-of-pam")
async def life_of_pam():
    return FileResponse(str(FRONTEND_DIR / "life-of-pam.html"))


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
