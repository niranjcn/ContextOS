function Invoke-ContextOS {
    param([string]$Target = "")

    $venv = ".\.venv\Scripts\python.exe"

    switch ($Target) {
        "install" {
            pip install -r requirements.txt
            & $venv -m spacy download en_core_web_sm
        }
        "install-dev" {
            pip install -r requirements-dev.txt
            & $venv -m spacy download en_core_web_sm
        }
        "install-dashboard" {
            Push-Location dashboard; npm install; Pop-Location
        }
        "run-api" {
            uvicorn core.api.main:app --host 127.0.0.1 --port 8000 --reload
        }
        "run-dashboard" {
            Push-Location dashboard; npm run dev; Pop-Location
        }
        "test" {
            & $venv -m pytest tests/ -v --cov=core --cov-report=term-missing
        }
        "test-fast" {
            & $venv -m pytest tests/ -x -q --no-header
        }
        "lint" {
            ruff check .; if ($?) { black --check . }
        }
        "format" {
            ruff check --fix .; ruff format .
        }
        "check-ollama" {
            curl -s http://localhost:11434/api/tags
        }
        "pull-models" {
            ollama pull llama3.2; ollama pull all-minilm
        }
        "connect-gmail" {
            & $venv -m cli.main connect gmail
        }
        "connect-gdrive" {
            & $venv -m cli.main connect gdrive
        }
        "sync-all" {
            & $venv -m cli.main sync
        }
        "cli-status" {
            & $venv -m cli.main status
        }
        "cli-serve" {
            & $venv -m cli.main serve
        }
        "docker-build" {
            docker build -t contextos-api:latest .
            docker build -t contextos-dashboard:latest ./dashboard
        }
        "docker-run" {
            docker compose up -d
        }
        "docker-stop" {
            docker compose down
        }
        "docker-logs" {
            docker compose logs -f
        }
        "docker-test" {
            docker compose up -d
            Start-Sleep -Seconds 10
            curl -f http://localhost:8000/health
            curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"question": "test"}'
        }
        default {
            Write-Host "Usage: .\run.psm1 <target>"
            Write-Host ""
            Write-Host "Available targets:"
            Write-Host "  install, install-dev, install-dashboard"
            Write-Host "  run-api, run-dashboard"
            Write-Host "  test, test-fast"
            Write-Host "  lint, format"
            Write-Host "  check-ollama, pull-models"
            Write-Host "  connect-gmail, connect-gdrive, sync-all"
            Write-Host "  cli-status, cli-serve"
            Write-Host "  docker-build, docker-run, docker-stop, docker-logs, docker-test"
        }
    }
}

Invoke-ContextOS @args
