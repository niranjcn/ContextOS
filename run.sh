#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ContextOS — One-command launcher via Docker
# =============================================================================
# Usage:
#   ./run.sh                  # Uses default model (llama3.2)
#   ./run.sh -m llama3.2:8b  # Custom model
# =============================================================================

MODEL="${MODEL:-llama3.2}"

while getopts "m:" opt; do
    case $opt in
        m) MODEL="$OPTARG" ;;
        *) echo "Usage: $0 [-m model]" && exit 1 ;;
    esac
done

echo ""
echo "==> Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    echo "ERROR: docker is not installed."
    echo "Install Docker Desktop from https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "ERROR: 'docker compose' (v2) is not available."
    echo "Update Docker Desktop to a version that includes docker compose v2."
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "==> Creating default .env file..."
    cat > .env <<EOF
CONTEXTOS_DATA_DIR=~/.contextos/data
CONTEXTOS_DB_DIR=~/.contextos/db
OLLAMA_MODEL=${MODEL}
ENABLE_ENCRYPTION=false
EOF
    echo "Created .env with defaults. You can edit it later."
fi

echo "==> Starting ContextOS (model: ${MODEL})..."
echo "First launch will download the LLM model (~2 GB). This may take a few minutes."
echo ""

docker compose up -d --build

echo "==> Waiting for API to become healthy..."

TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        STATUS=$(curl -sf http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
        if [ "$STATUS" = "healthy" ]; then
            echo "API is healthy!"
            break
        fi
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "WARNING: API did not report healthy within ${TIMEOUT}s."
    echo "Run 'docker compose logs api' to check for errors."
fi

echo ""
echo "==> ContextOS is running!"
echo "  Dashboard: http://localhost:5173"
echo "  API docs:  http://localhost:8000/docs"
echo "  API:       http://localhost:8000"
echo ""
echo "To stop:    docker compose down"
echo "To view logs: docker compose logs -f"
