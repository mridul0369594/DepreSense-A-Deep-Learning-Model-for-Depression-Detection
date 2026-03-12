# Environment Setup Guide

## Frontend Setup

### Prerequisites
- Node.js 16+
- npm or yarn

### Environment Variables
File: `frontend/.env`
```
VITE_API_BASE_URL=http://localhost:8000
```

### Installation
```bash
cd frontend
npm install
npm run dev
```

## Backend Setup

### Prerequisites
- Python 3.10+
- pip

### Environment Variables
File: `DepreSense-main/backend/.env`
```
# Firebase
FIREBASE_CREDENTIALS_PATH=./config/firebase-service-account.json
FIREBASE_API_KEY=your-api-key

# Server
DEBUG=False
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=WARNING

# CORS
ALLOWED_ORIGINS=http://localhost:8080,https://depresense.web.app

# File Upload
MAX_FILE_SIZE_MB=100
UPLOAD_DIR=./uploads

# OTP
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=3

# Email (Gmail)
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465

# Model
MODEL_PATH=../output/model/your_model_file

# Admin
ADMIN_SECRET_KEY=secret-key-for-admin-signup
```

### Installation
```bash
cd DepreSense-main/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Firebase Setup

1. Create Firebase project
2. Enable Authentication (Email/Password)
3. Create Firestore database
4. Download service account key
5. Save to `DepreSense-main/backend/config/firebase-service-account.json`

## Gmail SMTP Setup

1. Enable 2FA on Gmail
2. Generate App Password
3. Store in `SMTP_PASSWORD` in .env

## Deployment

See DEPLOYMENT.md for production setup.
