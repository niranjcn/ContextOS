.PHONY: install install-dev install-dashboard run-api run-dashboard run-all test test-fast lint format check-ollama pull-models \
	connect-gmail connect-gdrive sync-all cli-status cli-serve \
	docker-build docker-run docker-stop docker-logs docker-test

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
	$(MAKE) run-api &
	$(MAKE) run-dashboard

# ---- Test ----

test:
	pytest tests/ -v --cov=core --cov-report=term-missing

test-fast:
	pytest tests/ -x -q --no-header

# ---- Lint & Format ----

lint:
	ruff check . && black --check .

format:
	ruff check --fix . && ruff format .

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

# ---- Docker ----

docker-build:
	docker build -t contextos-api:latest .
	docker build -t contextos-dashboard:latest ./dashboard

docker-run:
	docker compose up -d

docker-stop:
	docker compose down

docker-logs:
	docker compose logs -f

docker-test:
	@echo "Starting stack..."
	docker compose up -d
	@echo "Waiting for services..."
	powershell -Command "Start-Sleep -Seconds 10"
	curl -f http://localhost:8000/health
	curl -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "test"}'
	@echo "\nSmoke tests passed!"


