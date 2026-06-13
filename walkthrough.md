# ContextOS — Docker Deployment Walkthrough

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for the Python API (builder + runtime) |
| `.dockerignore` | Excludes .venv, .git, secrets, tests from build context |
| `docker-compose.yml` | Full stack: Ollama + API + Dashboard + model puller |
| `dashboard/Dockerfile` | Multi-stage build: Node/Vite → nginx serving static files |
| `dashboard/nginx.conf` | SPA fallback, `/api` reverse proxy, gzip, caching headers |
| `run.ps1` | One-click launcher for Windows |
| `run.sh` | One-click launcher for macOS/Linux |

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Ollama     │◄───│     API      │◄───│  Dashboard   │
│  :11434      │    │   :8000      │    │   :5173      │
│  LLM Server  │    │  FastAPI     │    │  React/nginx │
└──────────────┘    └──────────────┘    └──────────────┘
        ▲
        │
┌──────────────┐
│ Model Puller │
│  (one-shot)  │
└──────────────┘
```

## One-Command Launch

### Windows
```powershell
.\run.ps1
```

### macOS / Linux
```bash
chmod +x run.sh
./run.sh
```

### Manual (any OS)
```bash
docker compose up -d --build
```

## Useful Commands

```bash
# View logs
docker compose logs -f

# Stop everything (data preserved)
docker compose down

# Stop everything and delete data
docker compose down -v

# Rebuild after code changes
docker compose up -d --build
```

## Access

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| API | http://localhost:8000 |
| Ollama | http://localhost:11434 |
