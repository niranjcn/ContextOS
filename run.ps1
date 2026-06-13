<#
.SYNOPSIS
    One-command launcher for ContextOS via Docker.
.DESCRIPTION
    Checks prerequisites, pulls the model, and starts the full ContextOS stack.
    Access the dashboard at http://localhost:5173 and the API at http://localhost:8000.
.EXAMPLE
    .\run.ps1
    .\run.ps1 -Model llama3.2:8b
#>

param(
    [string]$Model = "llama3.2"
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Check-Command($Name) {
    if (!(Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$Name' is not installed." -ForegroundColor Red
        Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        exit 1
    }
}

# --- Prerequisites ---
Write-Step "Checking prerequisites..."
Check-Command "docker"

$composeCmd = "docker compose"
try {
    $null = docker compose version
} catch {
    Write-Host "ERROR: 'docker compose' (v2) is not available." -ForegroundColor Red
    Write-Host "Update Docker Desktop to a version that includes docker compose v2." -ForegroundColor Yellow
    exit 1
}

# --- Check for .env ---
if (!(Test-Path ".env")) {
    Write-Step "Creating default .env file..."
    @"
CONTEXTOS_DATA_DIR=~/.contextos/data
CONTEXTOS_DB_DIR=~/.contextos/db
OLLAMA_MODEL=$Model
ENABLE_ENCRYPTION=false
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Created .env with defaults. You can edit it later." -ForegroundColor Green
}

# --- Start ---
Write-Step "Starting ContextOS (model: $Model)..."
Write-Host "First launch will download the LLM model (~2 GB). This may take a few minutes." -ForegroundColor Yellow
Write-Host ""

docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start containers." -ForegroundColor Red
    exit 1
}

# --- Wait for health ---
Write-Step "Waiting for API to become healthy..."
$timeout = 120
$elapsed = 0
while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
        if ($response.status -eq "healthy") {
            Write-Host "API is healthy!" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 3
    $elapsed += 3
    Write-Host "." -NoNewline
}
Write-Host ""

if ($elapsed -ge $timeout) {
    Write-Host "WARNING: API did not report healthy within $timeout seconds." -ForegroundColor Yellow
    Write-Host "Run 'docker compose logs api' to check for errors." -ForegroundColor Yellow
}

# --- Done ---
Write-Step "ContextOS is running!"
Write-Host "  Dashboard: http://localhost:5173" -ForegroundColor Green
Write-Host "  API docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  API:       http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "To stop:    docker compose down" -ForegroundColor Yellow
Write-Host "To view logs: docker compose logs -f" -ForegroundColor Yellow
