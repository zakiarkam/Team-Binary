# AI-Powered Digital Marketing Orchestration
# Team Binary · University of Moratuwa · 2026
#
#   make help     list every target
#   make setup    one-time install
#   make up       start everything
#   make demo     populate a full demonstration
#   make test     run every test suite

SHELL   := /bin/bash
PY      := venv/bin/python
PIP     := venv/bin/pip
UVICORN := venv/bin/uvicorn

.DEFAULT_GOAL := help
.PHONY: help setup db api web site demo test test-fast lint clean reset stop status train

help:  ## Show this help
	@echo "AI-Powered Digital Marketing Orchestration"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Typical first run:"
	@echo "  make setup      # once"
	@echo "  make db         # PostgreSQL in Docker"
	@echo "  make api        # terminal 2"
	@echo "  make web        # terminal 3"
	@echo "  make site       # terminal 4"
	@echo "  make demo       # populate everything"

setup:  ## Install Python and Node dependencies (one time)
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q -r api/requirements.txt
	$(PY) -m playwright install chromium
	cd web && npm install
	@test -f .env || cp .env.example .env
	@echo "✓ Setup complete. Next: make db"

db:  ## Start PostgreSQL (Docker)
	docker-compose up -d
	@printf "waiting for postgres"
	@for i in $$(seq 1 40); do \
		if [ "$$(docker inspect -f '{{.State.Health.Status}}' mos_postgres 2>/dev/null)" = "healthy" ]; then \
			echo " ✓"; exit 0; fi; printf "."; sleep 1; done; \
		echo " ✗ timed out"; exit 1

api:  ## Run the FastAPI backend (foreground)
	$(UVICORN) api.main:app --reload --port 8000

web:  ## Run the Next.js dashboard (foreground)
	cd web && npm run dev

site:  ## Serve the demo client website on :4000 (foreground)
	python3 -m http.server 4000 --directory demo-site

demo:  ## Populate a complete demonstration (needs db + api + site running)
	$(PY) scripts/demo_reset.py

train:  ## Retrain the Module 4 models
	$(PY) scripts/train_models.py

test:  ## Run every test suite
	$(PY) -m pytest tests/ -q
	cd modules/m3_analytics && ../../$(PY) -m pytest tests/ -q
	cd web && npm run build

test-fast:  ## Run the Python tests only, skipping slow ones
	$(PY) -m pytest tests/ -q -m "not slow"

status:  ## Show what is running
	@echo "postgres : $$(docker inspect -f '{{.State.Status}}' mos_postgres 2>/dev/null || echo 'not running')"
	@echo "api      : $$(curl -fsS http://localhost:8000/health 2>/dev/null || echo 'not responding')"
	@echo "dashboard: $$(curl -fsS -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo 'not responding')"
	@echo "demo site: $$(curl -fsS -o /dev/null -w '%{http_code}' http://localhost:4000 2>/dev/null || echo 'not responding')"

stop:  ## Stop PostgreSQL (data is kept)
	docker-compose down

reset:  ## Stop PostgreSQL and DELETE all its data
	docker-compose down -v
	@echo "✓ Database volume removed. `make db` will start from an empty schema."

clean:  ## Remove build caches
	find . -name __pycache__ -type d -not -path './venv/*' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache web/.next
	@echo "✓ Caches cleared."
