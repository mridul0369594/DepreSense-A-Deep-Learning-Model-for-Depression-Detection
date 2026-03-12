# ── Base image ──────────────────────────────────────────────
FROM python:3.11-slim

# ── Set working directory ──────────────────────────────────
WORKDIR /app

# ── Install dependencies first (layer caching) ────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy backend source code ──────────────────────────────
COPY . .

# ── Expose the API port ───────────────────────────────────
EXPOSE 8000

# ── Start the application ─────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
