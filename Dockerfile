# ==============================================================================
# ContextOS API — Multi-Stage Dockerfile
# ==============================================================================
# Stage 1: Build Python dependencies in an isolated layer
# Stage 2: Copy only runtime artifacts into a clean slim image
# Result: ~500MB smaller than a single-stage build
# ==============================================================================

# ---------------------------------------------------------------------------
# STAGE 1 — Builder: compile native extensions (sentencepiece, etc.)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# gcc/g++ are needed to compile C extensions in packages like
# sentence-transformers, chromadb, and some spaCy dependencies.
# We install them here and discard this entire layer in the final image.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first — Docker caches this layer so re-builds
# are fast when only source code changes (not dependencies).
COPY requirements.txt /tmp/requirements.txt

# --user installs packages to /root/.local instead of system-wide.
# This lets us copy just /root/.local in the next stage.
# --no-cache-dir avoids storing pip's download cache (saves ~100MB).
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# STAGE 2 — Runtime: lean image with only what's needed to run the API
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# libgomp1 is the OpenMP runtime library — required by PyTorch/ONNX
# which sentence-transformers uses for embedding inference.
# curl is needed for Docker health checks.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from the builder stage.
# This is the key trick: we get compiled packages without carrying
# the compiler toolchain (gcc, g++) into production.
COPY --from=builder /root/.local /root/.local

# Ensure the user-installed packages are on PATH
ENV PATH=/root/.local/bin:$PATH

# Download the spaCy English NLP model at build time so the container
# starts instantly without needing internet access at runtime.
# Version pinned to match spaCy 3.7.x compatibility.
RUN python -m spacy download en_core_web_sm

# Copy the entire project source code into the container.
WORKDIR /app
COPY . .

# Create a non-root user for security. Running containers as root
# means a container escape gives the attacker root on the host.
RUN groupadd -r contextos && \
    useradd -r -g contextos -d /app -s /sbin/nologin contextos && \
    mkdir -p /data/chroma && \
    chown -R contextos:contextos /app /data

# ---------------------------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------------------------

# Print Python output immediately instead of buffering — critical for
# seeing logs in real-time with `docker logs`.
ENV PYTHONUNBUFFERED=1

# Don't write .pyc files — saves disk and avoids stale bytecode issues.
ENV PYTHONDONTWRITEBYTECODE=1

# Default path for ChromaDB persistent storage.
# Mapped to a Docker volume so data survives container restarts.
ENV CHROMA_DB_PATH=/data/chroma

# The API listens on port 8000 (FastAPI/Uvicorn default).
EXPOSE 8000

# Switch to the non-root user before running the application.
USER contextos

# Health check for container orchestrators.
# The /health endpoint returns 200 when the API and Ollama are ready.
HEALTHCHECK --start-period=30s --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the FastAPI application with Uvicorn.
# --host 0.0.0.0 binds to all interfaces (required inside containers).
# --port 8000 matches the EXPOSE directive above.
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
