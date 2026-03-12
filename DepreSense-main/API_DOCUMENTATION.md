# DepreSense API Documentation

## Base URL
- **Local:** http://localhost:8000
- **Production:** https://depresense-backend-xxxxx.run.app

## Authentication
All endpoints except signup/login require:
```
Headers: {
  "Authorization": "Bearer {token}",
  "Content-Type": "application/json"
}
```

---

## AUTHENTICATION ENDPOINTS

### 1. User Signup
```
POST /auth/signup

Request:
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}

Response (201):
{
  "message": "Signup successful. Check email for OTP.",
  "email": "user@example.com",
  "status": "awaiting_otp"
}

Error (400):
{
  "error": "Email already exists"
}
```

### 2. Verify OTP
```
POST /auth/verify-otp

Request:
{
  "email": "user@example.com",
  "otp": "123456"
}

Response (200):
{
  "message": "Email verified successfully. You can now login.",
  "status": "verified"
}

Error (400):
{
  "error": "Invalid OTP"
}
```

### 3. Resend OTP
```
POST /auth/resend-otp

Request:
{
  "email": "user@example.com"
}

Response (200):
{
  "message": "OTP resent to your email"
}
```

### 4. User Login
```
POST /auth/login

Request:
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response (200):
{
  "token": "firebase-token-here",
  "user": {
    "uid": "user-id",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-03-10T..."
  }
}

Error (401):
{
  "error": "Invalid credentials"
}
```

### 5. Get Current User
```
GET /auth/me
Headers: Authorization: Bearer {token}

Response (200):
{
  "uid": "user-id",
  "email": "user@example.com",
  "name": "John Doe",
  "verified": true,
  "created_at": "2024-03-10T..."
}

Error (401):
{
  "error": "Unauthorized"
}
```

### 6. User Logout
```
POST /auth/logout
Headers: Authorization: Bearer {token}

Response (200):
{
  "message": "Logged out successfully"
}
```

---

## EEG FILE ENDPOINTS

### 7. Upload EEG File
```
POST /eeg/upload
Headers: 
  Authorization: Bearer {token}
  Content-Type: multipart/form-data

Body: FormData with file (binary .edf)

Response (201):
{
  "file_id": "unique-file-id",
  "filename": "eeg_recording.edf",
  "status": "uploaded",
  "uploaded_at": "2024-03-10T...",
  "file_size": 1024000
}

Error (400):
{
  "error": "Invalid file format. Only .edf files accepted."
}

Error (413):
{
  "error": "File too large. Max 100MB."
}
```

### 8. Get All EEG Files
```
GET /eeg/files
Headers: Authorization: Bearer {token}

Response (200):
[
  {
    "file_id": "file-1",
    "filename": "eeg1.edf",
    "file_size": 1024000,
    "upload_date": "2024-03-10T...",
    "processing_status": "completed"
  },
  ...
]
```

### 9. Get Specific EEG File
```
GET /eeg/files/{file_id}
Headers: Authorization: Bearer {token}

Response (200):
{
  "file_id": "file-1",
  "filename": "eeg1.edf",
  "original_filename": "patient_eeg.edf",
  "file_size": 1024000,
  "upload_date": "2024-03-10T...",
  "processing_status": "completed"
}

Error (404):
{
  "error": "File not found"
}
```

### 10. Delete EEG File
```
DELETE /eeg/files/{file_id}
Headers: Authorization: Bearer {token}

Response (200):
{
  "message": "File deleted successfully"
}

Error (404):
{
  "error": "File not found"
}
```

---

## PREDICTION ENDPOINTS

### 11. Run Prediction
```
POST /predictions/predict
Headers: Authorization: Bearer {token}

Request:
{
  "file_id": "unique-file-id"
}

Response (201):
{
  "prediction_id": "pred-id",
  "result": {
    "depression_probability": 0.85,
    "confidence": 0.92,
    "risk_level": "high",
    "timestamp": "2024-03-10T..."
  },
  "explanation": {
    "feature_importance": {
      "Cz": 0.45,
      "F7": 0.38,
      "Fz": 0.32,
      ...
    },
    "top_features": ["Cz", "F7", "Fz", "P4", "C4"],
    "explanation_summary": "High theta band activity in frontal regions..."
  },
  "message": "Prediction successful"
}

Error (503):
{
  "error": "Model not loaded"
}

Error (500):
{
  "error": "Model inference failed"
}
```

### 12. Get Prediction History
```
GET /predictions/history
Headers: Authorization: Bearer {token}

Response (200):
{
  "predictions": [
    {
      "prediction_id": "pred-1",
      "file_id": "file-1",
      "depression_probability": 0.85,
      "risk_level": "high",
      "confidence": 0.92,
      "created_at": "2024-03-10T..."
    },
    ...
  ],
  "count": 5
}
```

### 13. Get Specific Prediction
```
GET /predictions/{prediction_id}
Headers: Authorization: Bearer {token}

Response (200):
{
  "prediction_id": "pred-1",
  "result": {
    "depression_probability": 0.85,
    "confidence": 0.92,
    "risk_level": "high"
  },
  "explanation": {
    "feature_importance": {...},
    "top_features": [...],
    "explanation_summary": "..."
  }
}

Error (404):
{
  "error": "Prediction not found"
}
```

---

## PATIENT MANAGEMENT ENDPOINTS

### 14. Create Patient
```
POST /patients/create
Headers: Authorization: Bearer {token}

Request:
{
  "patient_name": "John Doe",
  "patient_id": "PT-005",
  "age": 35,
  "gender": "M",
  "notes": "Initial consultation"
}

Response (201):
{
  "success": true,
  "patient_id": "PT-005",
  "message": "Patient created successfully"
}
```

### 15. Get All Patients
```
GET /patients/list
Headers: Authorization: Bearer {token}

Response (200):
{
  "success": true,
  "patients": [
    {
      "patient_id": "PT-001",
      "patient_name": "John Doe",
      "age": 35,
      "gender": "M",
      "created_at": "2024-03-10T..."
    },
    ...
  ],
  "count": 3
}
```

### 16. Get Patient Details
```
GET /patients/{patient_id}
Headers: Authorization: Bearer {token}

Response (200):
{
  "success": true,
  "patient": {
    "patient_id": "PT-001",
    "patient_name": "John Doe",
    "age": 35,
    "gender": "M",
    "notes": "..."
  }
}
```

---

## ADMIN ENDPOINTS

### 17. Admin Login
```
POST /auth/admin/login

Request:
{
  "email": "mridul06027@gmail.com",
  "password": "12345678"
}

Response (200):
{
  "success": true,
  "token": "firebase-token",
  "user": {
    "uid": "admin-id",
    "email": "mridul06027@gmail.com",
    "name": "System Administrator",
    "role": "super_admin"
  }
}

Error (403):
{
  "error": "Not an admin account"
}
```

### 18. Get All Users (Admin)
```
GET /admin/users/list
Headers: Authorization: Bearer {admin_token}

Response (200):
{
  "success": true,
  "users": [
    {
      "uid": "user-1",
      "email": "user@example.com",
      "name": "John Doe",
      "created_at": "2024-03-10T...",
      "verified": true,
      "last_login": "2024-03-11T..."
    },
    ...
  ],
  "total_users": 10
}

Error (403):
{
  "error": "Admin access required"
}
```

### 19. Get Analytics Overview (Admin)
```
GET /admin/analytics/overview
Headers: Authorization: Bearer {admin_token}

Response (200):
{
  "success": true,
  "analytics": {
    "total_users": 10,
    "total_predictions": 45,
    "depression_cases": 18,
    "healthy_cases": 27,
    "average_confidence": 0.87,
    "depression_percentage": 40.0
  }
}
```

### 20. Get System Status (Admin)
```
GET /admin/system/status
Headers: Authorization: Bearer {admin_token}

Response (200):
{
  "success": true,
  "system_status": {
    "backend_running": true,
    "firebase_connected": true,
    "model_loaded": true,
    "database_available": true,
    "email_service": "active"
  }
}
```

### 21. Get System Logs (Admin)
```
GET /admin/system/logs
Headers: Authorization: Bearer {admin_token}

Response (200):
{
  "success": true,
  "logs": [
    {
      "timestamp": "2024-03-11T10:30:00",
      "level": "INFO",
      "message": "User login successful",
      "user_id": "user-1"
    },
    ...
  ],
  "total": 100
}
```

---

## HEALTH CHECK ENDPOINTS

### 22. API Health
```
GET /health

Response (200):
{
  "status": "ok",
  "version": "1.0.0"
}
```

### 23. Model Status
```
GET /health/model

Response (200):
{
  "model_loaded": true
}
```

### 24. Firebase Status
```
GET /health/firebase

Response (200):
{
  "firebase_connected": true
}
```

---

## ERROR RESPONSE FORMAT

All errors follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "User-friendly message",
    "status_code": 400,
    "timestamp": "2024-03-11T10:30:00Z"
  }
}
```

### Common Error Codes:
- `INVALID_FILE_FORMAT` (400)
- `FILE_TOO_LARGE` (413)
- `FILE_NOT_FOUND` (404)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `MODEL_NOT_LOADED` (503)
- `INFERENCE_ERROR` (500)
- `USER_NOT_FOUND` (404)
- `ADMIN_ACCESS_REQUIRED` (403)
- `INTERNAL_SERVER_ERROR` (500)

---

## RESPONSE STATUS CODES

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - No/invalid token |
| 403 | Forbidden - No permission |
| 404 | Not Found - Resource doesn't exist |
| 413 | Payload Too Large - File too big |
| 500 | Server Error - Backend error |
| 503 | Service Unavailable - Model not loaded |

---

## REQUEST EXAMPLES

### Using curl:
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'

# Upload file
curl -X POST http://localhost:8000/eeg/upload \
  -H "Authorization: Bearer {token}" \
  -F "file=@eeg_file.edf"

# Make prediction
curl -X POST http://localhost:8000/predictions/predict \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"file_id":"file-123"}'
```

### Using JavaScript/Fetch:
```javascript
// Login
const res = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'pass123'
  })
});
const data = await res.json();

// Make prediction
const pred = await fetch('http://localhost:8000/predictions/predict', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ file_id: 'file-123' })
});
```

---

## RATE LIMITING
- Default: 100 requests per minute per IP
- Admin endpoints: 50 requests per minute
- File upload: 5 files per minute

## PAGINATION
Endpoints returning lists support:
- `?limit=10` - Items per page
- `?offset=0` - Starting position
