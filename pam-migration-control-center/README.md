# PAM Migration Control Center

Interactive control center for the 80-week CyberArk PAM migration project. Visualizes the full migration journey — phases, agents, gates, wave execution, inputs/outputs/deliverables.

## Quick Start (One Command)

### Option 1: Docker (Recommended for Demos)

```bash
docker-compose up --build
```

Open **http://localhost:8080** in your browser.

### Option 2: Python (Development)

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8080
```

Open **http://localhost:8080** in your browser.

## What You'll See

| Page | Description |
|------|-------------|
| **Mission Control** | Dashboard with stats, phase timeline, agent status, risk profile, gate tracker |
| **Phase Explorer** | 8 expandable phase cards (P0-P7) with activities, deliverables, and drill-down |
| **Agent Orchestration** | 17 agent cards with status, click for detail panel and output viewer |
| **Wave Execution** | 5-wave breakdown, ETL pipeline animation, heartbeat validation |
| **Gate Tracker** | 17 human approval gates with simulation (click Approve to advance) |
| **Option Comparison** | Side-by-side Option A vs B with permission deep dive and platform mapping |
| **Status & Info** | Build status, what's needed for production, data import instructions |

## Key Features

- **Option A/B Toggle** — Switch between Secret Server and Privilege Cloud targets. All pages update.
- **Drill-Down** — Click any deliverable or agent output to see the actual JSON data.
- **ETL Simulation** — Click "Run Wave" to watch the 7-step pipeline animate.
- **Gate Approval** — Click "Approve" to advance gates through the critical path.
- **Data Import** — Upload your own JSON test data to replace mock data.

## Importing Custom Data

```bash
# Import a discovery manifest
curl -X POST http://localhost:8080/api/import/discovery \
  -F "file=@my_discovery.json"

# Import custom wave data
curl -X POST http://localhost:8080/api/import/waves \
  -F "file=@my_waves.json"

# Check what's imported
curl http://localhost:8080/api/import/status

# Clear and revert to mock data
curl -X DELETE http://localhost:8080/api/import/discovery
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/risks` | Risk breakdown |
| GET | `/api/dashboard/timeline` | Phase timeline |
| GET | `/api/phases` | All phases with option-specific content |
| GET | `/api/phases/{id}` | Single phase detail |
| GET | `/api/agents` | All 17 agents with status |
| GET | `/api/agents/{id}` | Agent detail |
| GET | `/api/agents/{id}/output` | Agent output data (drill-down) |
| GET | `/api/waves` | All 5 waves |
| POST | `/api/waves/{id}/simulate` | Simulate ETL pipeline |
| GET | `/api/gates` | All 17 gates |
| POST | `/api/gates/{id}/approve` | Approve a gate |
| POST | `/api/gates/reset` | Reset gates to initial state |
| GET | `/api/deliverables/{phase}` | Phase deliverables list |
| GET | `/api/deliverables/{phase}/{key}` | Deliverable data (drill-down) |
| POST | `/api/import/{type}` | Import custom data (JSON) |
| GET | `/api/import/status` | List imported files |
| DELETE | `/api/import/{type}` | Clear imported data |

## Architecture

```
Frontend (Vanilla JS)  →  FastAPI Backend  →  Mock Data / Imported Data
                                           ↓  (future)
                                     Real Agent Code (coordinator.py)
```

- **Frontend**: Single-page app, no build step. Same dark theme as all iOPEX deliverables.
- **Backend**: Python FastAPI serving static files + REST API.
- **Data**: Mock data matches real agent output formats. Import your own via `/api/import/`.

## Wiring to Real Agents (Future)

When ready to connect to live migration data, replace mock imports in each router:

```python
# Before (stub):
from backend.mock_data.data import AGENTS

# After (real):
from CyberArk_migration.coordinator import MigrationCoordinator
coordinator = MigrationCoordinator("config.json")
```

No frontend changes needed — same API contract, real data.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Frontend**: Vanilla HTML/CSS/JS, DM Sans + JetBrains Mono (Google Fonts)
- **Deployment**: Docker / docker-compose
- **Design**: Same dark theme palette as all iOPEX project deliverables
