# Multi-stage Dockerfile for Faultline (Node SPA build + Python 3.12 FastAPI runner)

# ── Stage 1: Build Frontend SPA ───────────────────────────────────────────────
FROM node:22-alpine AS web-builder
WORKDIR /app/web

# Copy package descriptors first to maximize layer cache
COPY web/package.json web/package-lock.json ./
RUN npm ci

# Copy web source and build production bundle
COPY web/ ./
RUN npm run build

# ── Stage 2: Python 3.12 Application Runner ───────────────────────────────────
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml ./
COPY graph/ /app/graph/
COPY agent/ /app/agent/
RUN pip install --no-cache-dir .

# Copy application source directories
COPY api/ /app/api/
COPY data/ /app/data/
COPY fixtures/ /app/fixtures/
COPY infra/ /app/infra/

# Copy built frontend distribution from web-builder
COPY --from=web-builder /app/web/dist /app/web/dist

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
