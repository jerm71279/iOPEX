.PHONY: run dev docker-up docker-down tunnel test-trigger test lint install

# ─── Run ──────────────────────────────────────────────────────────────────────
run:
	uvicorn contract_intelligence.main:app --host 0.0.0.0 --port 8000 --reload

dev:
	docker compose up docuseal -d && \
	uvicorn contract_intelligence.main:app --host 0.0.0.0 --port 8000 --reload

# ─── Docker ───────────────────────────────────────────────────────────────────
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# ─── Webhook Setup ────────────────────────────────────────────────────────────
# Reads the active ngrok tunnel from :4040 and updates DocuSeal webhook URL
tunnel:
	@echo "Fetching ngrok tunnel URL..."
	@NGROK_URL=$$(curl -s http://localhost:4040/api/tunnels | python3 -c \
		"import sys,json; t=json.load(sys.stdin)['tunnels']; \
		 print([x['public_url'] for x in t if 'https' in x['public_url']][0])") && \
	WEBHOOK_URL="$$NGROK_URL/webhooks/docuseal" && \
	echo "Setting DocuSeal webhook to: $$WEBHOOK_URL" && \
	curl -s -X PUT "$(DOCUSEAL_BASE_URL)/api/account" \
		-H "X-Auth-Token: $(DOCUSEAL_API_KEY)" \
		-H "Content-Type: application/json" \
		-d "{\"webhook_url\": \"$$WEBHOOK_URL\"}" && \
	echo "\nDone. Webhook configured."

# ─── Test Trigger ─────────────────────────────────────────────────────────────
# Usage: make test-trigger PDF=path/to/quote.pdf
test-trigger:
	@if [ -z "$(PDF)" ]; then echo "Usage: make test-trigger PDF=path/to/quote.pdf"; exit 1; fi
	curl -s -X POST http://localhost:8000/trigger/upload \
		-F "pdf=@$(PDF)" \
		-F "sender=test@trigger" | python3 -m json.tool

# ─── Tests ────────────────────────────────────────────────────────────────────
test:
	python3 -m pytest tests/ -v

# ─── Install ──────────────────────────────────────────────────────────────────
install:
	pip install -e ".[dev]"

# ─── Lint ─────────────────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/
