# DepreSense - Technology Stack Documentation

## FRONTEND TECHNOLOGY STACK

### Core Framework
- **Framework:** React 18.x
  - Why: Modern UI library, component-based architecture, large ecosystem
  - Used for: Building interactive user interfaces
  - Version: ^18.0.0

- **Build Tool:** Vite
  - Why: Fast build tool, instant HMR, optimized bundle size
  - Used for: Development server, production builds
  - Config: vite.config.ts

- **Language:** TypeScript
  - Why: Type safety, better IDE support, catch errors at compile time
  - Used for: All frontend code files (.tsx, .ts)
  - Benefits: Prevents runtime errors, improves code quality

### Styling & UI
- **CSS Framework:** Tailwind CSS
  - Why: Utility-first CSS, rapid UI development, consistent design
  - Used for: All component styling
  - Config: tailwind.config.ts
  - Benefits: No custom CSS, responsive design out of box

- **Icons:** Lucide React
  - Why: Beautiful, consistent icon library
  - Package: lucide-react@0.383.0
  - Used for: UI icons throughout application

### Routing & Navigation
- **Router:** React Router v6
  - Why: Standard routing library for React
  - Used for: Page navigation, protected routes
  - Key Routes:
    - /login - User login
    - /register - User registration
    - /verify-otp - OTP verification
    - /dashboard - Main dashboard
    - /mdd-detection - EEG analysis
    - /admin/login - Admin login
    - /admin/dashboard - Admin panel

### State Management
- **Context API** (built-in)
  - Why: Lightweight, no external dependencies
  - Used for: Global state (auth, user, admin)
  - Contexts:
    - AuthContext - Clinician authentication
    - AdminAuthContext - Admin authentication

### API Communication
- **HTTP Client:** Fetch API (built-in)
  - Why: Standard browser API, no external dependencies
  - Used for: All backend API calls
  - Headers: Authorization, Content-Type
  - Location: frontend/src/services/

- **Service Layer:** Custom API wrapper
  - File: frontend/src/services/api.ts
  - Functions: signup, login, makePrediction, uploadFile, etc.
  - Pattern: Promise-based, error handling included

### Authentication
- **Firebase Authentication**
  - Package: firebase (via Firebase Console)
  - Used for: User authentication, token generation
  - Methods:
    - Email/Password signup
    - Email/Password login
    - Custom tokens for admins
    - OTP verification via SMTP

### Data Visualization
- **Charts:** Recharts
  - Package: recharts
  - Used for: SHAP feature importance visualizations
  - Components: BarChart, custom visualizations

- **SHAP Visualization:** Custom component
  - File: frontend/src/components/SHAPVisualization.tsx
  - Displays: Feature importance for each EEG channel
  - Format: Bar chart with values

### Form Handling
- **Form Validation:** Pydantic (backend) + Manual (frontend)
  - Validation: Email format, password strength, file type
  - Error messages: User-friendly feedback

### File Handling
- **File Upload:** FormData + Fetch API
  - Accepts: .edf files only
  - Max size: 100MB (configurable)
  - Progress tracking: XHR upload events
  - Storage: Backend disk + Firestore metadata

### Storage
- **Session Storage:** localStorage
  - Stores: Auth tokens, admin tokens
  - Keys: authToken, adminToken
  - Persistence: Across page reloads

### Testing
- **Test Framework:** Vitest
  - Config: vitest.config.ts
  - Used for: Unit tests (if implemented)

### Development Tools
- **Package Manager:** npm
  - Lock file: package-lock.json
  - Command: npm install, npm run dev, npm run build

### Performance Optimizations
- Vite code splitting: Automatic
- Lazy loading: React.lazy() for routes
- Bundle size: ~550KB gzipped after Lovable removal
- Build time: ~15-20 seconds

---

## BACKEND TECHNOLOGY STACK

### Core Framework
- **Framework:** FastAPI
  - Why: Fast, modern Python framework, async support
  - Python: 3.10+
  - Used for: REST API endpoints, request/response handling
  - Port: 8000

- **ASGI Server:** Uvicorn
  - Why: ASGI server for FastAPI
  - Used for: Running the application
  - Command: uvicorn app.main:app --reload

- **Language:** Python 3.10+
  - Why: Scientific computing libraries, ML frameworks
  - Benefits: Rich ecosystem for data science

### API Framework
- **Validation:** Pydantic
  - Why: Data validation, type hints, error messages
  - Used for: Request/response schemas
  - Location: app/schemas/
  - Benefits: Automatic validation, swagger docs

- **CORS Handling:** FastAPI CORS Middleware
  - Why: Handle cross-origin requests from frontend
  - Config: Configurable allowed origins
  - Security: Prevents unauthorized domain access

### Data Processing & ML
- **EEG Processing:** MNE-Python
  - Package: mne
  - Used for: Reading .edf files, signal processing
  - Functions:
    - Reading EEG signals
    - Filtering (0.5-45 Hz bandpass)
    - Notch filtering (50 Hz)
    - Segmentation into windows

- **Data Science:** NumPy, SciPy
  - Packages: numpy, scipy
  - Used for: Numerical operations, signal processing
  - Functions: FFT, STFT, matrix operations

- **Machine Learning:** Scikit-learn
  - Package: scikit-learn
  - Used for: Preprocessing, feature scaling
  - Functions: Normalization, standardization

### Deep Learning & Models
- **ML Framework:** TensorFlow (or PyTorch - specify which)
  - Package: tensorflow
  - Used for: CNN model for EEG classification
  - Model: CNN-Souping (multiple CNNs + weight averaging)
  - Input: EEG spectrogram (2D images)
  - Output: Depression probability (0-1)

- **Model Loading:** joblib
  - Package: joblib
  - Used for: Loading trained model weights
  - Location: app/models/model_loader.py
  - Model path: ../output/model/

### Explainability & Interpretability
- **SHAP (SHapley Additive exPlanations)**
  - Package: shap
  - Used for: Feature importance visualization
  - Method: KernelExplainer / DeepExplainer
  - Output: SHAP values for each EEG channel
  - Purpose: Explain which brain regions contribute most

- **Grad-CAM** (optional)
  - Used for: Spatial attention visualization
  - Shows: Which EEG regions are important

### Authentication & Security
- **Firebase Admin SDK**
  - Package: firebase-admin
  - Used for:
    - User authentication
    - Custom token generation
    - User management
  - Config: service account JSON key

- **OTP Verification**
  - Method: SMTP email
  - Used for: Secure user/admin signup verification
  - Expiry: 5 minutes
  - Max attempts: 3

### Database & Storage
- **Firebase Firestore**
  - Type: NoSQL document database
  - Used for:
    - User profiles
    - EEG file metadata
    - Prediction results
    - Admin records
  - Collections:
    - users/{uid}/
    - admins/
    - otp_codes/

- **File Storage:** Local disk + Firebase Storage
  - Used for: Temporary .edf file storage
  - Location: backend/uploads/
  - Metadata: Stored in Firestore

### Email Service
- **SMTP:** Python smtplib
  - Service: Gmail SMTP
  - Used for: OTP email delivery
  - Config: SMTP credentials in .env
  - Security: App-specific passwords

### Logging & Monitoring
- **Logging:** Python logging module
  - Level: DEBUG, INFO, WARNING, ERROR
  - Output: Console + file
  - Location: backend/logs/
  - Purpose: Error tracking, debugging

### Testing
- **Framework:** Pytest
  - Package: pytest
  - Used for: Unit tests, integration tests
  - Location: app/tests/
  - Coverage: 114+ tests passing

### Containerization
- **Docker**
  - File: Dockerfile
  - Base: Python 3.11 slim
  - Used for: Containerized deployment
  - Registry: Google Container Registry (GCR)

### Deployment
- **Cloud Platform:** Google Cloud
  - Service: Cloud Run (serverless)
  - Region: us-central1
  - Scaling: Automatic based on demand
  - Configuration: Environment variables in Cloud Run

---

## ARCHITECTURE DIAGRAM
```
┌─────────────────────────────────────────────────────┐
│              Frontend (React + Vite)                │
├─────────────────────────────────────────────────────┤
│  Components | Pages | Services | Contexts           │
│  ↓                                                   │
│  API Service Layer (fetch)                          │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/JSON
                       ↓
┌─────────────────────────────────────────────────────┐
│           Backend (FastAPI on Cloud Run)            │
├─────────────────────────────────────────────────────┤
│  Routes (Auth, EEG, Predictions, Admin)             │
│  ↓                                                   │
│  Services (Preprocessing, ML, SHAP, OTP)            │
│  ↓                                                   │
│  Models (ML Model, Model Loader)                    │
│  ↓                                                   │
│  Middleware (Auth, Error Handling)                  │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    Firebase      Firebase        Gmail
    Auth        Firestore         SMTP
    (Firebase Console)
```

---

## DATA FLOW
```
User Login
  → POST /auth/login
  → Firebase Auth verification
  → Firestore user check
  → Return token + user data
  → Frontend stores token in localStorage

EEG Upload & Prediction
  → POST /eeg/upload (file)
  → Validate .edf format
  → Save to disk + Firestore metadata
  → POST /predictions/predict (file_id)
  → Preprocessing (filtering, segmentation, STFT)
  → ML Model inference (CNN-Souping)
  → SHAP explanation generation
  → Save to Firestore
  → Return result + explanation to frontend
  → Display in UI

Admin Dashboard
  → POST /admin/login
  → Firebase Auth + admin verification
  → GET /admin/users/list
  → GET /admin/analytics/overview
  → GET /admin/system/logs
  → Display analytics/users/logs

OTP Flow
  → User signup email
  → Generate random 6-digit OTP
  → Send via Gmail SMTP
  → User enters OTP
  → Verify OTP in Firestore
  → Mark user as verified
  → Allow login
```

---

## TECHNOLOGY CHOICES & RATIONALE

| Technology | Why Chosen | Alternatives Considered |
|-----------|-----------|------------------------|
| React | Component-based, large ecosystem, team familiarity | Vue, Angular |
| FastAPI | Fast, async, auto-documentation, type hints | Flask, Django |
| Firebase | Easy auth, serverless DB, real-time sync | PostgreSQL, MongoDB |
| TensorFlow | Industry standard ML, CNN support, SHAP integration | PyTorch, Keras |
| Tailwind | Rapid UI dev, utility classes, responsive | Bootstrap, Material-UI |
| Cloud Run | Serverless, auto-scaling, pay-per-use | EC2, App Engine |
| Firestore | Real-time DB, easy integration with Firebase | PostgreSQL, DynamoDB |
| SHAP | Model explainability, clinical credibility | Lime, Attention Maps |
| MNE | EEG signal processing, open-source | Custom signal processing |
| Google Cloud | Firebase integration, Cloud Run, Storage | AWS, Azure |
