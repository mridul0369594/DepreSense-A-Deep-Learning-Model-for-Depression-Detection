---
description: How to run E2E integration tests for frontend-backend
---

# End-to-End Integration Testing Workflow

## Prerequisites

1. Python 3.11 with `requests` library installed
2. Node.js 18+ with npm

## Steps

// turbo-all

1. Start the backend server:
```
cd DepreSense-main/backend
py -3.11 -m uvicorn app.main:app --reload --port 8000
```
Wait for "Application startup complete" in the logs.

2. Start the frontend dev server:
```
cd frontend
npm run dev
```
Wait for the Vite ready message showing `http://localhost:8080/`.

3. Run the automated E2E test script:
```
cd .
py -3.11 test_e2e_integration.py
```

4. Check TypeScript compilation:
```
cd frontend
npx tsc --noEmit
```

5. Run backend unit tests:
```
cd DepreSense-main/backend
py -3.11 -m pytest tests/ -x --tb=short -q
```

6. Build the production frontend bundle:
```
cd frontend
npx vite build
```

## Firebase Setup (Required for Auth Tests)

Without Firebase credentials, only health and CORS tests will pass.
To enable the full test suite:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create or select your project
3. Go to Project Settings > Service Accounts > Generate new private key
4. Save the JSON file as `DepreSense-main/backend/config/firebase-service-account.json`
5. Go to Project Settings > General > Web API Key
6. Set `FIREBASE_API_KEY=<your-key>` in `DepreSense-main/backend/.env`
7. Restart the backend server

## Test Checklist

- [ ] Health endpoints respond correctly
- [ ] CORS allows http://localhost:8080
- [ ] Signup creates user in Firebase
- [ ] Login returns token
- [ ] Token validates via /auth/me
- [ ] EEG file upload works with progress
- [ ] Prediction returns result + SHAP
- [ ] History shows past predictions
- [ ] Logout clears token
- [ ] Invalid token → 401
- [ ] Service unavailable → 503 with friendly message
- [ ] File too large → error message
- [ ] Invalid file type → error message
