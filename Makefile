.PHONY: install install-dev run-api run-dashboard run-all test test-fast lint format check-ollama pull-models connect-gmail sync-all

# ---- Setup ----

install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

install-dev:
	pip install -r requirements-dev.txt
	python -m spacy download en_core_web_sm
	pre-commit install

install-dashboard:
	cd dashboard && npm install

# ---- Run ----

run-api:
	uvicorn core.api.main:app --host 127.0.0.1 --port 8000 --reload

run-dashboard:
	cd dashboard && npm run dev

run-all:
	@echo "Starting API server in background..."
	uvicorn core.api.main:app --host 127.0.0.1 --port 8000 --reload &
	@echo "Starting dashboard..."
	cd dashboard && npm run dev

# ---- Test ----

test:
	pytest tests/ -v --cov=core --cov-report=term-missing

test-fast:
	pytest tests/ -x -q --no-header

# ---- Lint & Format ----

lint:
	ruff check . && black --check .

format:
	black . && ruff check --fix .

# ---- Ollama ----

check-ollama:
	curl -s http://localhost:11434/api/tags | python3 -m json.tool

pull-models:
	ollama pull llama3.2
	ollama pull all-minilm

# ---- Connectors ----

connect-gmail:
	python -m cli.main connect gmail

connect-gdrive:
	python -m cli.main connect gdrive

sync-all:
	python -m cli.main sync

# ---- CLI shortcuts ----

cli-status:
	python -m cli.main status

cli-serve:
	python -m cli.main serve
