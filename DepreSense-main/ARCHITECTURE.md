# DepreSense System Architecture

## High-Level Architecture
```
┌──────────────────────────────────────────────────────────┐
│                    Frontend Layer                         │
│                   (React + Vite)                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Clinician Portal │ Admin Dashboard │ Auth Pages      │ │
│  └─────────────────────────────────────────────────────┘ │
│               ↓                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  API Service Layer │ Contexts │ Components         │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON (Port 8080)
                       ↓
┌──────────────────────────────────────────────────────────┐
│          API Gateway / Middleware Layer                  │
│  (CORS, Auth, Error Handling, Logging)                   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON (Port 8000)
                       ↓
┌──────────────────────────────────────────────────────────┐
│                  Backend API Layer                       │
│                   (FastAPI)                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Auth Routes │ EEG Routes │ Prediction Routes      │ │
│  │ Admin Routes │ Patient Routes │ Health Checks      │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    ┌───────────┐ ┌──────────┐ ┌────────────┐
    │ Services  │ │ Firebase │ │   File     │
    │ Layer     │ │ Services │ │ Operations │
    │           │ │          │ │            │
    │ - EEG     │ │ - Auth   │ │ - Upload   │
    │ Process   │ │ - DB     │ │ - Storage  │
    │ - Model   │ │          │ │            │
    │ - SHAP    │ │          │ │            │
    │ - OTP     │ │          │ │            │
    └───────────┘ └──────────┘ └────────────┘
```

## Request/Response Flow

### User Authentication Flow
```
1. User enters credentials (frontend)
   ↓
2. Frontend calls POST /auth/login
   ↓
3. Backend verifies with Firebase Auth
   ↓
4. Backend creates custom token
   ↓
5. Frontend stores token in localStorage
   ↓
6. All subsequent requests include token in header
   ↓
7. Middleware verifies token before processing request
```

### EEG Analysis Flow
```
1. User uploads .edf file (frontend)
   ↓
2. Frontend calls POST /eeg/upload with file
   ↓
3. Backend validates file format and size
   ↓
4. Backend saves file to disk
   ↓
5. Backend stores metadata in Firestore
   ↓
6. Frontend calls POST /predictions/predict with file_id
   ↓
7. Backend preprocessing:
   - Read .edf file using MNE
   - Filter signal (bandpass + notch)
   - Segment into windows
   - Apply STFT/CWT for spectrogram
   ↓
8. Backend model inference:
   - Load CNN-Souping model
   - Run prediction on spectrogram
   - Get probability + confidence
   ↓
9. Backend SHAP explanation:
   - Initialize SHAP explainer
   - Generate feature importance
   - Return top 5 important channels
   ↓
10. Backend saves prediction to Firestore
    ↓
11. Frontend receives result + explanation
    ↓
12. Frontend displays:
    - Prediction probability (%)
    - Risk level (Low/Medium/High)
    - Confidence score
    - SHAP bar chart
    - Top important EEG channels
```

## Deployment Architecture

### Production Deployment
```
┌─────────────────────────────────────────────────┐
│           Firebase Hosting                       │
│  (Frontend: React static build)                  │
└────────────────┬────────────────────────────────┘
                 │ HTTPS
                 ↓
┌─────────────────────────────────────────────────┐
│        Google Cloud Run                          │
│  (Backend: FastAPI container)                    │
│  - Auto-scaling                                  │
│  - Serverless (pay per request)                  │
│  - Environment variables                         │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ↓                 ↓
    ┌──────────┐    ┌──────────┐
    │ Firebase │    │ Firebase │
    │   Auth   │    │ Firestore│
    │          │    │   DB     │
    └──────────┘    └──────────┘
```

## Component Interaction Diagram
```
Frontend Components
├── AuthPages (Login, Signup, OTP)
│   └── Calls: auth/login, auth/signup, auth/verify-otp
│
├── ClinicianPortal
│   ├── Dashboard
│   ├── MDDDetection (EEG Upload)
│   │   └── Calls: eeg/upload, predictions/predict
│   ├── PatientManagement
│   │   └── Calls: patients/list, patients/create
│   └── PredictionHistory
│       └── Calls: predictions/history
│
└── AdminDashboard
    ├── UserManagement
    │   └── Calls: admin/users/list
    ├── AnalyticsView
    │   └── Calls: admin/analytics/overview
    └── SystemStatus
        └── Calls: admin/system/status

Backend Routes
├── /auth/* (Authentication)
├── /eeg/* (EEG File Management)
├── /predictions/* (Model Predictions)
├── /patients/* (Patient Management)
├── /admin/* (Admin Functions)
└── /health (Health Checks)
```

## Data Persistence

### What's Stored Where?

**Firebase Authentication:**
- User credentials
- Email verification status
- Password hashes

**Firestore Database:**
- User profiles
- EEG file metadata
- Prediction results
- SHAP explanations
- Admin records
- OTP codes
- Activity logs

**Local Disk (Server):**
- Uploaded .edf files (temporary)
- Application logs
- Model weights (loaded into memory)

**Browser (Frontend):**
- Auth token (localStorage)
- User session data (Context)
- Recent uploads (Context)

## Security Layers

1. **Authentication:**
   - Firebase Auth (cryptographically secure)
   - OTP verification (email-based, 5 min expiry)
   - JWT tokens (backend verification)

2. **Authorization:**
   - Role-based access control (clinician, admin, super_admin)
   - User isolation (can only access own data)
   - Admin verification for admin endpoints

3. **Data Protection:**
   - HTTPS/TLS encryption in transit
   - Firestore security rules
   - Input validation (Pydantic)

4. **Monitoring:**
   - Activity logging (all API calls)
   - Error tracking
   - System health checks

## Scalability Considerations

### Frontend (React + Vite)
- Static deployment on Firebase Hosting
- CDN distribution globally
- Scales infinitely (no backend)

### Backend (FastAPI on Cloud Run)
- Serverless architecture
- Auto-scales based on requests
- Load balancing automatic
- Pay only for what you use

### Database (Firestore)
- NoSQL (scales horizontally)
- Auto-sharding
- Real-time synchronization
- Handles millions of documents

### Model Inference
- Single model loaded in memory
- Inference time: ~5.7 seconds per file
- Parallel processing possible (multiple container instances)
- Can optimize with model quantization

## Performance Optimization

### Frontend
- Code splitting (React lazy loading)
- Image optimization (Vite)
- Gzip compression
- Browser caching

### Backend
- Connection pooling (Firebase)
- Batch operations (Firestore)
- Caching (model in memory)
- Async/await for I/O operations

### Database
- Proper indexing
- Query optimization
- Denormalization where appropriate
- Archive old logs

## Disaster Recovery

- **Database:** Firestore automated backups
- **Code:** Version control (Git)
- **Secrets:** Environment variables stored in Cloud Run
- **Logs:** Stored in Firestore and local files
