# DepreSense Backend — Deployment Guide

Complete instructions for deploying the DepreSense backend to production.

---

## Table of Contents

- [Pre-deployment Checklist](#pre-deployment-checklist)
- [Environment Setup](#environment-setup)
- [Docker Build & Push](#docker-build--push)
- [Deployment Options](#deployment-options)
- [Running in Production](#running-in-production)
- [Health Monitoring](#health-monitoring)
- [Scaling Considerations](#scaling-considerations)
- [Rollback Procedures](#rollback-procedures)

---

## Pre-deployment Checklist

Before deploying, verify every item:

| # | Check | Command / Action |
|---|-------|------------------|
| 1 | All tests passing | `make test` (expect 100+ tests, 0 failures) |
| 2 | Coverage ≥ 80% | `make test-coverage` → open `htmlcov/index.html` |
| 3 | Debug mode OFF | `.env` → `DEBUG=False` |
| 4 | Production log level | `.env` → `LOG_LEVEL=WARNING` |
| 5 | Firebase credentials secured | `config/firebase-service-account.json` exists, not in git |
| 6 | CORS set to production domain | `ALLOWED_ORIGINS=https://yourdomain.com` |
| 7 | Model file accessible | `MODEL_PATH` points to a valid model directory |
| 8 | `requirements.txt` frozen | No loose version specs for core deps |
| 9 | Secrets not in code | No API keys, passwords, or credentials in source |
| 10 | `.env.example` up-to-date | All variables documented |

---

## Environment Setup

Create a production `.env` file with:

```env
# ── Firebase ─────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
FIREBASE_API_KEY=your-production-api-key

# ── Model ────────────────────────────────────────────────
MODEL_PATH=/app/model
SCALER_PATH=/app/assets/scaler_ec.pkl
SHAP_BACKGROUND_PATH=/app/assets/shap_bg_ec.npy
CHANNEL_ORDER_PATH=/app/assets/channel_order.json

# ── Application ──────────────────────────────────────────
DEBUG=False
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://yourdomain.com

# ── Upload ───────────────────────────────────────────────
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=/app/uploads
```

> **Security:** Never commit the production `.env` to version control. Use environment variables or secrets management (AWS Secrets Manager, GCP Secret Manager, etc.) in production.

---

## Docker Build & Push

### Build the image

```bash
docker build -t depresense-backend:latest .
```

### Tag for your registry

```bash
# Docker Hub
docker tag depresense-backend:latest your-user/depresense-backend:v1.0.0

# AWS ECR
docker tag depresense-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/depresense-backend:v1.0.0

# Google Artifact Registry
docker tag depresense-backend:latest us-central1-docker.pkg.dev/your-project/depresense/backend:v1.0.0
```

### Push

```bash
docker push your-registry/depresense-backend:v1.0.0
```

---

## Deployment Options

### 1. Google Cloud Run (Recommended for MVP)

```bash
# Build and deploy in one step
gcloud run deploy depresense-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DEBUG=False,LOG_LEVEL=WARNING" \
  --memory 2Gi \
  --cpu 2 \
  --port 8000
```

**Pros:** Auto-scaling, pay-per-use, managed TLS  
**Cons:** Cold starts (~5s with model loading)

### 2. AWS ECS (Fargate)

```bash
# Create task definition
aws ecs register-task-definition \
  --family depresense-backend \
  --container-definitions '[{
    "name": "backend",
    "image": "your-registry/depresense-backend:v1.0.0",
    "portMappings": [{"containerPort": 8000}],
    "memory": 2048,
    "cpu": 1024,
    "essential": true
  }]'
```

### 3. DigitalOcean App Platform

```yaml
# .do/app.yaml
name: depresense-backend
services:
  - name: backend
    dockerfile_path: Dockerfile
    http_port: 8000
    instance_size_slug: professional-xs
    health_check:
      http_path: /health
```

### 4. Custom VPS (Ubuntu + Docker)

```bash
# On your VPS
ssh your-server
docker pull your-registry/depresense-backend:v1.0.0
docker run -d \
  --name depresense \
  -p 8000:8000 \
  --env-file /opt/depresense/.env \
  -v /opt/depresense/model:/app/model \
  -v /opt/depresense/uploads:/app/uploads \
  --restart unless-stopped \
  your-registry/depresense-backend:v1.0.0
```

---

## Running in Production

### Use Gunicorn (not uvicorn with --reload)

```bash
# Production command (replaces the Dockerfile CMD)
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

Add `gunicorn` to `requirements.txt` for production:
```
gunicorn==21.2.0
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## Health Monitoring

### Endpoints to monitor

| Endpoint | Interval | Alerts |
|----------|----------|--------|
| `GET /health` | 30s | Down if non-200 for 3 consecutive checks |
| `GET /health/model` | 60s | Alert if `model_loaded: false` for >5 min |
| `GET /health/firebase` | 60s | Alert if `firebase_connected: false` for >5 min |

### Logging

Configure log aggregation:

```bash
# Docker logging driver (send to CloudWatch, Stackdriver, etc.)
docker run ... --log-driver=awslogs \
  --log-opt awslogs-group=depresense-backend \
  --log-opt awslogs-region=us-east-1
```

### Key metrics to track

- Response latency (P50, P95, P99)
- Error rate (5xx responses / total)
- Model inference time
- Memory usage
- Active connections
- EEG file upload size distribution

---

## Scaling Considerations

### Horizontal Scaling

- **Stateless design:** The API is stateless — all state lives in Firestore
- **Shared uploads:** Mount a shared volume (EFS, GCS FUSE) for `/app/uploads` across replicas
- **Model loading:** Each replica loads its own copy (~100 MB RAM)

### Recommended sizing

| Load | Workers | CPU | RAM | Notes |
|------|---------|-----|-----|-------|
| Light (< 10 rps) | 2 | 1 vCPU | 2 GB | Single container |
| Medium (10-50 rps) | 4 | 2 vCPU | 4 GB | 2 containers + load balancer |
| Heavy (50+ rps) | 8+ | 4+ vCPU | 8+ GB | Auto-scaling group |

### Database (Firestore)

- Firestore auto-scales reads/writes
- Monitor `google.firestore.document.read` and `write` quotas
- Consider composite indexes for prediction history queries

---

## Rollback Procedures

### Quick rollback (Docker)

```bash
# Stop current version
docker stop depresense

# Start previous version
docker run -d --name depresense \
  your-registry/depresense-backend:v0.9.0 ...
```

### Blue-green deployment

1. Deploy new version alongside old (different container name)
2. Run health checks against new version
3. Switch load balancer to new version
4. Keep old version running for 30 minutes
5. Remove old version

### If something goes wrong

1. **Immediate:** Roll back to last known good Docker image
2. **Check logs:** `docker logs depresense --tail 100`
3. **Check health:** `curl https://api.yourdomain.com/health`
4. **Check model:** `curl https://api.yourdomain.com/health/model`
5. **Check Firebase:** `curl https://api.yourdomain.com/health/firebase`
