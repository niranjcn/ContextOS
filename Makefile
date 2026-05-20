.PHONY: install install-dev run-api test lint format check-ollama pull-model

install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

install-dev:
	pip install -r requirements-dev.txt
	python -m spacy download en_core_web_sm
	pre-commit install

run-api:
	uvicorn core.api.main:app --host 127.0.0.1 --port 8000 --reload

test:
	pytest tests/ -v --cov=core --cov-report=term-missing

lint:
	ruff check . && black --check .

format:
	black . && ruff check --fix .

check-ollama:
	curl -s http://localhost:11434/api/tags | python3 -m json.tool

pull-model:
	ollama pull llama3.2
	ollama pull all-minilm
