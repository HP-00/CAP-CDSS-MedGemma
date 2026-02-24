# =============================================================================
# CAP CDSS — Multi-stage Docker build
# Stage 1: Build Vite SPA (Node)
# Stage 2: Python GPU runtime (CUDA) + serve API + static frontend
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Frontend build
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python GPU runtime
# ---------------------------------------------------------------------------
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip python3.11-dev \
    git curl && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY pyproject.toml README.md ./
COPY src/ src/
COPY server/ server/
COPY tests/ tests/
COPY benchmark_data/ benchmark_data/

# Install the package with server extras + PyTorch CUDA
RUN python3 -m pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cu124 && \
    python3 -m pip install --no-cache-dir -e ".[server]"

# Copy built frontend → server/static for FastAPI to serve
COPY --from=frontend-builder /app/frontend/dist /app/server/static/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Cloud Run expects port 8080
EXPOSE 8080

CMD ["python3", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
