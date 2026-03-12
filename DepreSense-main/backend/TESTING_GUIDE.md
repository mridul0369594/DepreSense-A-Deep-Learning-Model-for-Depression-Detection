# DepreSense — Frontend-Backend Integration Testing Guide

Step-by-step guide for testing the full DepreSense stack locally.

---

## 1. Setup Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env — set FIREBASE_CREDENTIALS_PATH, FIREBASE_API_KEY, MODEL_PATH

# Start backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify:**

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

curl http://localhost:8000/health/model
# Expected: {"model_loaded":true}
```

---

## 2. Setup Frontend

1. Start your React/Vite frontend (default port 5173 or 3000).
2. Set the API base URL in your frontend code to `http://localhost:8000`.
3. Ensure `ALLOWED_ORIGINS` in `backend/.env` includes your frontend URL:
   ```
   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

---

## 3. Test Authentication Flow

### 3.1 Sign Up

**Request (from frontend or curl):**

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!", "name": "Test User"}'
```

**Expected response (201):**

```json
{
  "token": "<firebase-id-token>",
  "user": {
    "uid": "abc123...",
    "email": "test@example.com",
    "name": "Test User",
    "created_at": "2026-02-25T15:00:00Z"
  },
  "message": "Account created successfully"
}
```

**Verify:**
- User appears in Firebase Console → Authentication
- User document created in Firestore → `users/{uid}`

### 3.2 Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!"}'
```

**Expected response (200):**

```json
{
  "token": "<firebase-id-token>",
  "user": { "uid": "...", "email": "test@example.com", "name": "Test User" },
  "message": "Login successful"
}
```

**Verify:**
- Store the `token` — all subsequent requests need it in the `Authorization: Bearer <token>` header.
- `last_login` updated in Firestore.

### 3.3 Get Current User

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

**Expected response (200):**

```json
{
  "uid": "...",
  "email": "test@example.com",
  "name": "Test User",
  "created_at": "2026-02-25T15:00:00Z"
}
```

---

## 4. Test EEG Upload

### 4.1 Upload an EDF File

```bash
curl -X POST http://localhost:8000/eeg/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/your/recording.edf"
```

**Expected response (201):**

```json
{
  "file_id": "a1b2c3d4...",
  "filename": "a1b2c3d4.edf",
  "status": "uploaded",
  "message": "File uploaded successfully",
  "uploaded_at": "2026-02-25T15:05:00Z"
}
```

**Verify:**
- File saved to `backend/uploads/` directory.
- Metadata created in Firestore → `users/{uid}/eeg_files/{file_id}`.
- Save the `file_id` for predictions.

### 4.2 List Files

```bash
curl http://localhost:8000/eeg/files \
  -H "Authorization: Bearer <token>"
```

**Expected:** Array of `EEGFileInfo` objects.

### 4.3 Get File Info

```bash
curl http://localhost:8000/eeg/files/<file_id> \
  -H "Authorization: Bearer <token>"
```

---

## 5. Test Predictions

### 5.1 Run Prediction

```bash
curl -X POST http://localhost:8000/predictions/predict \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "<file_id>"}'
```

**Expected response (201):**

```json
{
  "result": {
    "prediction_id": "e5f6g7h8...",
    "depression_probability": 0.6234,
    "risk_level": "medium",
    "confidence": 0.2468,
    "timestamp": "2026-02-25T15:10:00Z"
  },
  "explanation": {
    "feature_importance": { "Fp1": {...}, "Fp2": {...}, ... },
    "top_features": ["Fp1", "F3", "Cz", "P3", "O1"],
    "base_value": 0.6234,
    "explanation_summary": "The model predicts a medium risk of depression..."
  },
  "message": "Prediction completed successfully"
}
```

**Verify:**
- `risk_level` is one of: `low`, `medium`, `high`.
- `top_features` contains EEG channel names.
- EEG file status updated to `"completed"` in Firestore.
- Prediction saved in Firestore → `users/{uid}/predictions/{prediction_id}`.

### 5.2 Prediction History

```bash
curl http://localhost:8000/predictions/history \
  -H "Authorization: Bearer <token>"
```

### 5.3 Specific Prediction

```bash
curl http://localhost:8000/predictions/<prediction_id> \
  -H "Authorization: Bearer <token>"
```

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| **CORS error** in browser console | Frontend origin not in `ALLOWED_ORIGINS` | Add your frontend URL to `ALLOWED_ORIGINS` in `.env` and restart |
| **401 Unauthorized** | Missing or expired token | Log in again and use the new token in `Authorization: Bearer <token>` |
| **403 Forbidden** | Token valid but wrong user | Ensure you're using the correct account |
| **503 Model not loaded** | `MODEL_PATH` incorrect or model file missing | Check `MODEL_PATH` in `.env` points to a directory containing `soup_model_EC.keras` |
| **Firebase errors** | Credentials not configured | Set `FIREBASE_CREDENTIALS_PATH` in `.env` to your service-account JSON |
| **422 Preprocessing error** | EDF file is corrupt or wrong format | Use a valid 19-channel EEG `.edf` file |
| **413 File too large** | File exceeds `MAX_FILE_SIZE_MB` | Increase `MAX_FILE_SIZE_MB` in `.env` or use a smaller file |
| **Connection refused** | Backend not running | Start backend with `make run` or `python -m uvicorn ...` |
| **Slow predictions** | Large EDF file / many epochs | Normal — first prediction may take 10-30s depending on hardware |

### Checking Logs

Console logs appear in the terminal running the backend.
File logs are written to `logs/depresense.log`.

```bash
# View recent logs
tail -f logs/depresense.log        # macOS / Linux
Get-Content logs/depresense.log -Tail 20 -Wait   # PowerShell
```

Each log line includes a timestamp, level, module, and message:
```
2026-02-25 15:00:00  INFO  [depresense.api]  → GET /health  req_id=abc123...
2026-02-25 15:00:00  INFO  [depresense.api]  ← 200  1.3 ms  req_id=abc123...
```

### Verifying Firestore Data

1. Open [Firebase Console](https://console.firebase.google.com/)
2. Go to **Firestore Database**
3. Check these collections:
   - `users/{uid}` — user profile with `created_at`, `last_login`
   - `users/{uid}/eeg_files/{file_id}` — uploaded file metadata
   - `users/{uid}/predictions/{prediction_id}` — prediction results
