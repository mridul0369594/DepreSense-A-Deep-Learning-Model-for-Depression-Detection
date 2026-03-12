# 🧠 DepreSense  
### AI-Powered EEG Depression Detection Platform

> **DepreSense** is a full-stack AI platform that detects **Major Depressive Disorder (MDD)** from EEG brain signals using **deep learning and explainable AI**.  
> Clinicians can upload EEG recordings and receive **interpretable depression predictions** through an interactive web dashboard.

---

# ✨ Key Highlights

🔬 **AI-Driven EEG Analysis**  
Detect depression using brainwave patterns extracted from `.edf` EEG recordings.

🧠 **CNN-Souping Deep Learning Model**  
An ensemble CNN architecture that improves robustness and prediction stability.

📊 **Explainable AI (SHAP)**  
Visualizes **which EEG channels contributed most to the prediction**, enabling interpretable clinical insights.

🌐 **Full-Stack Clinical Platform**  
Secure web application allowing clinicians to upload EEG data and analyze results instantly.

👨‍⚕️ **Patient Management System**  
Store patient EEG records and track historical predictions.

🛡 **Secure Authentication System**  
Firebase authentication with **OTP email verification**.

☁ **Cloud-Native Infrastructure**  
Serverless deployment using **Google Cloud Run + Firebase**.

---

# 🏗 System Architecture
Frontend (React + Vite)
        │
        │ REST API
        ▼
Backend API (FastAPI)
        │
        ├── EEG Processing (MNE + SciPy)
        ├── Deep Learning Inference (CNN-Souping)
        ├── Explainability (SHAP)
        ├── Authentication (Firebase)
        └── File Management
        │
        ▼
Firebase Cloud Services
├── Firestore Database
├── Firebase Authentication
└── Cloud Infrastructure

# ⚙ Machine Learning Pipeline
EEG (.edf)
    │
    ▼
Signal Preprocessing
• Bandpass Filter (0.5–45Hz)
• Notch Filter (50Hz)
• Segmentation into epochs
    │
    ▼
Spectrogram Generation
(STFT / CWT)
    │
    ▼
CNN-Souping Deep Learning Model
    │
    ▼
Prediction Output
• Depression Probability
• Risk Level
• Confidence Score
    │
    ▼
SHAP Explainability
• Channel Importance
• Top Contributing Brain Regions


⏱ **Average inference time:** ~5.7 seconds per EEG file

---

# 🧠 Explainable AI

DepreSense integrates **SHAP GradientExplainer** to interpret model predictions.

### EEG Channels Analysed
Fp1 Fp2 F7 F8 F3 F4 T3 T4
C3 C4 Fz Cz Pz P3 P4 T5
T6 O1 O2


### Explanation Output

• Channel-level feature importance  
• Top contributing EEG electrodes  
• Directional influence on prediction  

This enables **transparent and clinically interpretable AI decisions**.

---

# 🛠 Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
React 18 | UI framework |
TypeScript | Type safety |
Vite | Fast development build tool |
TailwindCSS | Utility-first styling |
React Router | Client-side routing |
Recharts | SHAP visualizations |

---

## Backend

| Technology | Purpose |
|---|---|
FastAPI | REST API framework |
Python 3.10+ | Backend language |
Pydantic | Request validation |
Uvicorn | ASGI server |

---

## Machine Learning

| Technology | Purpose |
|---|---|
TensorFlow / PyTorch | Deep learning framework |
MNE-Python | EEG signal processing |
NumPy / SciPy | Numerical computing |
Scikit-learn | Data preprocessing |
SHAP | Model explainability |

---

## Cloud Infrastructure

| Technology | Purpose |
|---|---|
Firebase Auth | Authentication |
Firestore | NoSQL database |
Google Cloud Run | Serverless backend |
Docker | Containerization |

---

# 📡 Core API Modules

| Module | Description |
|------|-------------|
`/auth` | Authentication & OTP verification |
`/eeg` | EEG file upload & management |
`/predictions` | Model inference & SHAP explanation |
`/patients` | Patient record management |
`/admin` | System analytics & monitoring |
`/health` | Backend health checks |

---

# 🗄 Database Design

Firestore collections structure:
users/
 ├── eeg_files/
 └── predictions/

admins/

otp_codes/

system_logs/
✔ User-level data isolation
✔ Role-based access control
✔ Secure Firestore rules

---

# 🚀 Installation

## Frontend

```bash
cd frontend
npm install
npm run dev

Environment variable:
VITE_API_BASE_URL=http://localhost:8000

Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

Example .env configuration:

FIREBASE_CREDENTIALS_PATH=...
MODEL_PATH=...
SHAP_BG_PATH=...
SMTP_EMAIL=...
SMTP_PASSWORD=...

☁ Deployment

Production architecture:

Frontend → Firebase Hosting
Backend → Google Cloud Run
Database → Firestore
Authentication → Firebase Auth

✔ Serverless
✔ Auto-scaling
✔ Pay-per-use infrastructure

🔒 Security

• Firebase Authentication
• Email OTP verification
• JWT token authorization
• Role-based access control
• HTTPS encryption
• Firestore security rules

🧪 Testing

Backend uses pytest with extensive unit tests covering:

• Prediction pipeline
• SHAP explainability
• API endpoints
• Data validation

Run tests:

cd backend
pytest
📂 Project Structure
DepreSense
│
├── frontend
│   ├── components
│   ├── pages
│   ├── services
│   └── contexts
│
├── backend
│   ├── routes
│   ├── services
│   ├── models
│   ├── schemas
│   └── tests
│
├── output
│   ├── model
│   └── assets
│
└── docs
👥 Contributors
Name	Role

Mohamed Zeedhan	ML Lead
Mridul Bhattacharjee	Backend Developer
Mohamed Muzni Mohamed Ziham	Frontend Developer
☁ Deployment

Production architecture:

Frontend → Firebase Hosting
Backend → Google Cloud Run
Database → Firestore
Authentication → Firebase Auth

✔ Serverless
✔ Auto-scaling
✔ Pay-per-use infrastructure

🔒 Security

• Firebase Authentication
• Email OTP verification
• JWT token authorization
• Role-based access control
• HTTPS encryption
• Firestore security rules

🧪 Testing

Backend uses pytest with extensive unit tests covering:

• Prediction pipeline
• SHAP explainability
• API endpoints
• Data validation

Run tests:

cd backend
pytest
📂 Project Structure
DepreSense
│
├── frontend
│   ├── components
│   ├── pages
│   ├── services
│   └── contexts
│
├── backend
│   ├── routes
│   ├── services
│   ├── models
│   ├── schemas
│   └── tests
│
├── output
│   ├── model
│   └── assets
│
└── docs
👥 Contributors
Name	Role
Mohamed Zeedhan	ML Lead
Mridul Bhattacharjee	Backend Developer
Mohamed Muzni Mohamed Ziham	Frontend Developer
Rozin Khan	UI/UX Designer
Syed Athif Usman	Data Scientist

Taylor’s University — School of Computer Science

⚠ Disclaimer

DepreSense is a research and educational project.
It is not intended to replace professional clinical diagnosis.

Taylor’s University — School of Computer Science

⚠ Disclaimer

DepreSense is a research and educational project.
It is not intended to replace professional clinical diagnosis.
