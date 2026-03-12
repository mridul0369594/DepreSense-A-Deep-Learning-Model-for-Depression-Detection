# ── Render.com Production Dockerfile ────────────────────────
# Render builds from this Dockerfile automatically.
# Build context: DepreSense-main/ directory (set in render.yaml)

FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ───────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (cached layer) ────────────────────
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Backend source code ───────────────────────────────────
COPY backend/app/ ./app/
COPY backend/config/ ./config/

# ── Production environment ────────────────────────────────
COPY backend/.env.production ./.env

# ── ML Model & SHAP assets ───────────────────────────────
COPY output/model/ ./output/model/
COPY output/assets/ ./output/assets/

# ── Create directories ───────────────────────────────────
RUN mkdir -p /tmp/uploads logs

# ── Expose port (Render sets PORT env var) ────────────────
EXPOSE 8000

# ── Start command ─────────────────────────────────────────
# Render sets $PORT automatically; uvicorn reads it
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 120
