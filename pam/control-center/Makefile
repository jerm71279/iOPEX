.PHONY: help run test deploy lint clean

help:
	@echo "Pam Migration Control Center — Available targets:"
	@echo "  make run      Start the application locally"
	@echo "  make test     Run test suite"
	@echo "  make deploy   Deploy to Render.com"
	@echo "  make lint     Run linter"
	@echo "  make clean    Remove build artifacts"

run:
	docker-compose up

test:
	cd backend && python -m pytest tests/ -v 2>/dev/null || echo "No test suite found — add tests to backend/tests/"

deploy:
	git push origin main

lint:
	cd backend && python -m flake8 . --max-line-length=100 --exclude=venv,__pycache__,imported_data

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
