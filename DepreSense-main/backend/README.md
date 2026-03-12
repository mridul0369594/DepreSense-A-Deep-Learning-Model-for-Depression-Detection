# DepreSense Backend

**AI-powered EEG-based depression detection API** — Upload EEG recordings, run deep-learning inference, and receive SHAP-explained risk assessments.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **pip**
- **Firebase project** with service-account credentials
- **Trained model** files in `../output/model/`

### 1. Install dependencies

```bash
make install
# or: pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
FIREBASE_API_KEY=your-firebase-web-api-key
MODEL_PATH=../output/model
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Run locally

**Option A — Direct Python (recommended for development):**

```bash
make run
# → http://localhost:8000
```

**Option B — Docker:**

```bash
make run-docker
# → http://localhost:8000
```

### 4. Verify

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "1.0.0"}
```

### 5. Connect your frontend

Set your frontend's API base URL to `http://localhost:8000`. Make sure `ALLOWED_ORIGINS` in `.env` includes your frontend's dev server URL.

### 6. Stop / Logs

```bash
make stop     # Stop Docker containers
make logs     # Tail Docker logs
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | FastAPI + Uvicorn |
| **Auth / Database** | Firebase Admin SDK + Cloud Firestore |
| **EEG Processing** | MNE-Python, SciPy, NumPy, Pandas |
| **ML Inference** | TensorFlow / Keras |
| **Explainability** | SHAP |
| **Testing** | pytest, pytest-cov, httpx |
| **Containerization** | Docker, Docker Compose |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic-settings configuration
│   ├── routes/                 # API endpoint handlers
│   │   ├── auth.py             #   Signup, login, me, logout
│   │   ├── eeg.py              #   Upload, list, get, delete EEG files
│   │   ├── health.py           #   Health checks (API, model, Firebase)
│   │   └── predictions.py      #   Run prediction, get history
│   ├── schemas/                # Pydantic request/response models
│   │   ├── user.py             #   SignupRequest, LoginRequest, UserResponse
│   │   ├── eeg.py              #   EEGUploadResponse, EEGFileInfo
│   │   └── prediction.py       #   PredictionRequest/Response, ShapExplanation
│   ├── services/               # Business logic
│   │   ├── eeg_processor.py    #   EDF validation and reading
│   │   ├── model_inference.py  #   Model prediction + risk mapping
│   │   ├── shap_explainer.py   #   SHAP feature importance generation
│   │   └── firestore_service.py #  All Firestore CRUD operations
│   ├── middleware/             # Request/response processing
│   │   ├── auth_middleware.py  #   Firebase ID token verification
│   │   ├── error_handler.py    #   Global exception handling
│   │   └── logging_middleware.py # Request logging + X-Request-ID
│   ├── models/                 # ML model loading
│   │   └── model_loader.py     #   Lazy model + SHAP background loader
│   └── utils/                  # Helper utilities
│       ├── firebase_client.py  #   Firebase Admin SDK init
│       ├── file_handler.py     #   File save/delete/validate
│       ├── logger.py           #   Structured logging setup
│       └── request_context.py  #   Per-request context (request ID, user)
├── tests/                      # Test suite (100+ tests)
│   ├── conftest.py             #   Shared fixtures, mock Firebase
│   ├── test_auth.py            #   Authentication endpoint tests
│   ├── test_eeg.py             #   EEG upload/management tests
│   ├── test_predictions.py     #   Prediction endpoint tests
│   ├── test_error_handling.py  #   Error response format tests
│   ├── test_services.py        #   Service-layer unit tests
│   ├── test_health.py          #   Health check tests
│   ├── test_integration.py     #   End-to-end workflow tests
│   └── test_api_local.py       #   Smoke tests (live server)
├── logs/                       # Runtime log files
├── uploads/                    # Uploaded EEG files
├── config/                     # Firebase credentials (gitignored)
├── .env.example                # Environment variable template
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Local dev orchestration
├── Makefile                    # Developer commands
├── pytest.ini                  # Test configuration
├── requirements.txt            # Python dependencies
├── DEPLOYMENT.md               # Production deployment guide
├── CONTRIBUTING.md             # Contribution guidelines
└── TESTING_GUIDE.md            # Frontend integration testing
```

---

## API Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | No | API status |
| `GET` | `/health` | No | Health check (`status: ok`, `version`) |
| `GET` | `/health/model` | No | ML model loaded status |
| `GET` | `/health/firebase` | No | Firebase connection status |

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/signup` | No | Create account → returns token |
| `POST` | `/auth/login` | No | Login → returns token |
| `GET` | `/auth/me` | Bearer | Get current user profile |
| `POST` | `/auth/logout` | Bearer | Revoke refresh tokens |

### EEG Files

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/eeg/upload` | Bearer | Upload `.edf` file |
| `GET` | `/eeg/files` | Bearer | List user's uploaded files |
| `GET` | `/eeg/files/{file_id}` | Bearer | Get specific file metadata |
| `DELETE` | `/eeg/files/{file_id}` | Bearer | Delete file from disk + Firestore |

### Predictions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/predictions/predict` | Bearer | Run prediction on uploaded EEG |
| `GET` | `/predictions/history` | Bearer | Get all past predictions |
| `GET` | `/predictions/{prediction_id}` | Bearer | Get specific prediction + SHAP |

### Interactive docs

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `FIREBASE_CREDENTIALS_PATH` | `config/firebase-service-account.json` | Path to Firebase service account JSON |
| `FIREBASE_API_KEY` | — | Firebase Web API Key (for auth REST API) |
| `MODEL_PATH` | `../output/model` | Directory containing `.keras` model file |
| `SCALER_PATH` | `../output/assets/scaler_ec.pkl` | Fitted scaler for EEG preprocessing |
| `SHAP_BACKGROUND_PATH` | `../output/assets/shap_bg_ec.npy` | SHAP background data |
| `CHANNEL_ORDER_PATH` | `../output/assets/channel_order.json` | EEG channel ordering |
| `DEBUG` | `False` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins |
| `MAX_FILE_SIZE_MB` | `50` | Max EEG file upload size (MB) |
| `UPLOAD_DIR` | `uploads` | Directory for uploaded files |

---

## Testing

### Run tests

```bash
# Full suite
make test

# Fast tests only (skip integration/slow)
make test-fast

# With coverage report
make test-coverage
# → Open htmlcov/index.html for detailed report

# Specific file
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::TestSignup::test_signup_success -v
```

### Test files

| File | Tests | Focus |
|------|-------|-------|
| `test_auth.py` | 15 | Signup, login, me, logout |
| `test_eeg.py` | 16 | Upload, list, get, delete EEG files |
| `test_predictions.py` | 17 | Predict, history, get specific |
| `test_error_handling.py` | 19 | Error codes, response format, security |
| `test_services.py` | 25+ | Risk mapping, inference, SHAP, Firestore |
| `test_health.py` | 9 | Health endpoints, response time |
| `test_integration.py` | 12+ | Full auth/EEG/prediction flows |
| **Total** | **110+** | |

### Coverage

```bash
make test-coverage
# Generates htmlcov/index.html — open in browser
# Target: ≥ 80% line coverage
```

---

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the full production deployment guide including:

- Pre-deployment checklist
- Docker build & push instructions
- Google Cloud Run, AWS ECS, DigitalOcean, and VPS setups
- Gunicorn + Nginx configuration
- Health monitoring and alerts
- Scaling and rollback procedures

**Quick production start:**

```bash
# Build
docker build -t depresense-backend:latest .

# Run with production settings
docker run -d -p 8000:8000 \
  --env-file .env.prod \
  -v /path/to/model:/app/model \
  depresense-backend:latest
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `firebase_connected: false` | Missing credentials file | Set `FIREBASE_CREDENTIALS_PATH` in `.env` to your service account JSON |
| `model_loaded: false` | Model file not found | Check `MODEL_PATH` points to a directory with `soup_model_EC.keras` |
| `401 MISSING_TOKEN` | No Authorization header | Add `Authorization: Bearer <token>` header |
| `401 TOKEN_EXPIRED` | Token expired | Re-login to get a fresh token |
| `400 INVALID_FILE_TYPE` | Non-EDF upload | Only `.edf` files are accepted |
| `413 FILE_TOO_LARGE` | File exceeds limit | Increase `MAX_FILE_SIZE_MB` in `.env` |
| `422 PREPROCESSING_ERROR` | Bad EDF content | Verify the EDF file has valid EEG channels |
| `503 MODEL_NOT_LOADED` | Model not ready | Wait for model to load or check `MODEL_PATH` |
| CORS error in browser | Frontend origin not allowed | Add your frontend URL to `ALLOWED_ORIGINS` |
| Port already in use | Another process on 8000 | Kill the process or change `PORT` in `.env` |

### Checking logs

```bash
# Application log file
cat logs/depresense.log

# Last 50 lines (PowerShell)
Get-Content logs/depresense.log -Tail 50

# Docker logs
make logs
```

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines on:

- Development environment setup
- Code standards (PEP 8, type hints, docstrings)
- Testing requirements (≥ 80% coverage)
- Pull request process
- Bug reporting

---

## License

This project is part of a research study. See the LICENSE file for details.
