# BT Autonomous Healing

Static frontend demo for BT/EE network autonomous healing and self-remediation visualization.

## Stack
- **Frontend**: Vanilla HTML/CSS/JS — no build step required
- **Deployment**: Render.com static site (`render.yaml`)

## Key Files
```
frontend/
  index.html          Main demo SPA
  js/                 Dashboard logic
  css/                Styling
render.yaml           Render.com static site config
```

## Run Commands
```bash
# Local preview
cd frontend && python3 -m http.server 8080
# Then open http://localhost:8080
```

## Deploy
Render.com auto-deploys from main branch on push — no build step, static files only.

## Notes
- Demo app for BT/EE engagement context
- Related: BT Excalibur (EE Single ID Step 4, Profile + BACS sync) — see project memory
- No backend, no API calls — all data is mocked in JS
