# Component-Specific Technologies

## 1. Authentication System
- **Frontend:** React hooks, Context API
- **Backend:** Firebase Auth, Firebase SDK
- **Security:** JWT tokens (Firebase generated), OTP via SMTP
- **Database:** Firestore (users, otp_codes collections)
- **Email:** Gmail SMTP (Python smtplib)

## 2. EEG Processing Pipeline
- **File Reading:** MNE-Python (reads .edf format)
- **Filtering:** SciPy (bandpass 0.5-45Hz, notch 50Hz)
- **Segmentation:** NumPy (2-5 second windows)
- **Transform:** STFT/CWT (frequency-time representation)
- **Framework:** TensorFlow/PyTorch (depends on your model)

## 3. Machine Learning Model
- **Architecture:** CNN-Souping (multiple CNNs + weight averaging)
- **Input:** 2D spectrogram (frequency × time × channels)
- **Output:** Probability (0-1), risk level (low/medium/high)
- **Framework:** TensorFlow / PyTorch
- **Inference:** FastAPI backend service
- **Latency:** ~5.7 seconds per file

## 4. Explainability (SHAP)
- **Library:** SHAP (SHapley Additive exPlanations)
- **Method:** KernelExplainer or DeepExplainer
- **Output:** Feature importance for each EEG channel
- **Visualization:** Bar chart (Recharts on frontend)
- **Purpose:** Show which brain regions/frequencies matter

## 5. Patient Management
- **Frontend:** React components, forms
- **Backend:** FastAPI routes, patient service
- **Database:** Firestore (users/{uid}/patients/ collection)
- **CRUD:** Create, Read, Update, Delete operations

## 6. Admin Dashboard
- **Frontend:** React pages, charts, tables
- **Backend:** Admin routes, admin service
- **Database:** Firestore (admins/ collection)
- **Analytics:** Aggregated user data, prediction stats
- **Monitoring:** System status, activity logs

## 7. File Upload & Storage
- **Frontend:** FormData, Fetch API with progress
- **Backend:** Python multipart file handling
- **Storage:** Local disk (uploads/ directory) + Firestore metadata
- **Validation:** .edf format only, max 100MB
- **Security:** Authentication required, user isolation

## 8. PDF Report Generation
- **Backend:** Python PDF library (e.g., reportlab)
- **Data:** Prediction results, SHAP explanation, user info
- **Format:** Professional clinical report
- **Delivery:** Download from frontend

## 9. Logging & Monitoring
- **Frontend:** Browser console, DevTools
- **Backend:** Python logging module
- **Storage:** Log files (backend/logs/)
- **Level:** DEBUG, INFO, WARNING, ERROR
- **Cloud:** Google Cloud Logging (optional)

## 10. Deployment Infrastructure
- **Container:** Docker
- **Registry:** Google Container Registry (GCR)
- **Orchestration:** Cloud Run (serverless)
- **Configuration:** Environment variables, .env file
- **Scaling:** Automatic based on demand
- **Database:** Firestore (serverless)
- **Authentication:** Firebase (managed service)
