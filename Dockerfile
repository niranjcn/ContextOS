# ==============================================================================
# ContextOS API — Single-Stage Dockerfile
# ==============================================================================

FROM python:3.11-slim

# Install system dependencies:
#   - gcc/g++/build-essential: compile C extensions (sentence-transformers, chromadb, etc.)
#   - libgomp1: OpenMP runtime for PyTorch/ONNX
#   - curl: Docker health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first — Docker caches this layer so re-builds
# are fast when only source code changes (not dependencies).
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies.
# --no-cache-dir avoids storing pip's download cache (saves ~100MB).
#
# Order matters for size and reliability:
#   1. CPU-only PyTorch first — avoids pulling in ~2GB of CUDA packages
#      that sentence-transformers would otherwise install from the default index.
#   2. Everything from requirements.txt (torch is already installed, so pip
#      skips the CUDA variant).
#   3. openai-whisper WITH --no-build-isolation because its setup.py relies on
#      pkg_resources which is missing in pip's modern PEP 517 isolated build env.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir --no-build-isolation openai-whisper==20240930

# Download the spaCy English NLP model at build time via pip URL
# (python -m spacy download fails on yanked/old versions).
RUN pip install --no-cache-dir \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Copy the entire project source code into the container.
WORKDIR /app
COPY . .

# Create a non-root user for security.
RUN groupadd -r contextos && \
    useradd -r -g contextos -d /app -s /sbin/nologin contextos && \
    mkdir -p /data/chroma && \
    chown -R contextos:contextos /app /data

# Environment Configuration
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CHROMA_DB_PATH=/data/chroma
EXPOSE 8000

# Health check
HEALTHCHECK --start-period=30s --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

USER contextos

# Start the FastAPI application with Uvicorn.
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
