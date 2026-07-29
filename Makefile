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
.PHONY: help setup db db-brew db-docker db-create api web site demo research \
        test test-fast lint clean reset stop status train

help:  ## Show this help
	@echo "AI-Powered Digital Marketing Orchestration"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Typical first run:"
	@echo "  make setup      # once"
	@echo "  make db         # PostgreSQL (Homebrew or Docker)"
	@echo "  make api        # terminal 2"
	@echo "  make web        # terminal 3"
	@echo "  make site       # terminal 4"
	@echo "  make demo       # import the audience and run every module"
	@echo "  make research   # reproduce every experiment and figure"

setup:  ## Install Python and Node dependencies (one time)
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q -r api/requirements.txt
	$(PY) -m playwright install chromium
	cd web && npm install
	@test -f .env || cp .env.example .env
	@echo "✓ Setup complete. Next: make db"

# Postgres runs either as a Homebrew service or in Docker. Homebrew is tried
# first: it has one moving part instead of a virtual machine, and a corrupted
# Docker image store once took the whole database down the day before a demo.
# Docker remains supported for anyone who prefers it  `make db-docker`.
db:  ## Start PostgreSQL (Homebrew if present, else Docker)
	@if command -v pg_isready > /dev/null 2>&1 || \
	    [ -x /opt/homebrew/opt/postgresql@16/bin/pg_isready ]; then \
		$(MAKE) --no-print-directory db-brew; \
	else \
		$(MAKE) --no-print-directory db-docker; \
	fi

db-brew:  ## Start PostgreSQL as a Homebrew service (port 5434)
	@brew services start postgresql@16 > /dev/null 2>&1 || true
	@printf "waiting for postgres"
	@for i in $$(seq 1 30); do \
		if /opt/homebrew/opt/postgresql@16/bin/pg_isready -h localhost -p 5434 \
		   > /dev/null 2>&1; then echo " ✓"; exit 0; fi; printf "."; sleep 1; done; \
		echo " ✗ timed out"; exit 1

db-docker:  ## Start PostgreSQL in Docker
	docker-compose up -d
	@printf "waiting for postgres"
	@for i in $$(seq 1 40); do \
		if [ "$$(docker inspect -f '{{.State.Health.Status}}' mos_postgres 2>/dev/null)" = "healthy" ]; then \
			echo " ✓"; exit 0; fi; printf "."; sleep 1; done; \
		echo " ✗ timed out"; exit 1

db-create:  ## One-time: create the mos role and marketing_os database (Homebrew)
	@PATH="/opt/homebrew/opt/postgresql@16/bin:$$PATH"; \
	psql -h localhost -p 5434 -d postgres -v ON_ERROR_STOP=1 -c \
	  "DO \$$\$$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mos') \
	   THEN CREATE ROLE mos LOGIN PASSWORD 'mos_dev_password' CREATEDB; END IF; END \$$\$$;" \
	  && (createdb -h localhost -p 5434 -O mos marketing_os 2>/dev/null || true) \
	  && echo "✓ role and database ready"

api:  ## Run the FastAPI backend (foreground)
	$(UVICORN) api.main:app --reload --port 8000

web:  ## Run the Next.js dashboard (foreground)
	cd web && npm run dev

site:  ## Serve the demo client store on :4000 (foreground)
	python3 -m http.server 4000 --directory demo-site

demo:  ## Build the full research demonstration (needs db + api + site running)
	$(PY) scripts/build_research_demo.py

research:  ## Run every experiment and rebuild the report's figures
	$(PY) -m research.run_all

train:  ## Retrain the Module 4 models
	$(PY) scripts/train_models.py

test:  ## Run every test suite
	$(PY) -m pytest tests/ -q
	cd modules/m3_analytics && ../../$(PY) -m pytest tests/ -q
	cd web && npm run build

test-fast:  ## Run the Python tests only, skipping slow ones
	$(PY) -m pytest tests/ -q -m "not slow"

status:  ## Show what is running
	@echo "postgres : $$(/opt/homebrew/opt/postgresql@16/bin/pg_isready -h localhost -p 5434 2>/dev/null \
		|| docker inspect -f '{{.State.Status}}' mos_postgres 2>/dev/null \
		|| echo 'not running')"
	@echo "api      : $$(curl -fsS http://localhost:8000/health 2>/dev/null || echo 'not responding')"
	@echo "dashboard: $$(curl -fsS -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo 'not responding')"
	@echo "demo site: $$(curl -fsS -o /dev/null -w '%{http_code}' http://localhost:4000 2>/dev/null || echo 'not responding')"

stop:  ## Stop PostgreSQL (data is kept)
	@brew services stop postgresql@16 2>/dev/null || docker-compose down

reset:  ## Drop the database and recreate it empty
	@if /opt/homebrew/opt/postgresql@16/bin/pg_isready -h localhost -p 5434 > /dev/null 2>&1; then \
		PATH="/opt/homebrew/opt/postgresql@16/bin:$$PATH"; \
		dropdb -h localhost -p 5434 --if-exists marketing_os && \
		createdb -h localhost -p 5434 -O mos marketing_os && \
		echo "✓ Database recreated empty."; \
	else \
		docker-compose down -v && \
		echo "✓ Database volume removed."; \
	fi

clean:  ## Remove build caches
	find . -name __pycache__ -type d -not -path './venv/*' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache web/.next
	@echo "✓ Caches cleared."
