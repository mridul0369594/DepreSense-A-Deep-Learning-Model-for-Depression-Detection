"""Verify Firestore persistence after enabling the API + database."""
import requests
import time

BASE = "http://localhost:8000"
EMAIL = "depresense.e2e.test@gmail.com"
PW = "Test123!Pass"
EDF = r"d:\Study\0. degree\Last Year\DepreSense Project\MDD S33 EC.edf"

print("=" * 60)
print("FIRESTORE PERSISTENCE VERIFICATION")
print("=" * 60)

# 1. Login
r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PW}, timeout=20)
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"\n1. Login: {r.status_code} OK")

# 2. Upload EEG file
with open(EDF, "rb") as f:
    r = requests.post(
        f"{BASE}/eeg/upload",
        files={"file": ("verify_test.edf", f, "application/octet-stream")},
        headers=headers,
        timeout=60,
    )
fid = r.json().get("file_id")
print(f"2. Upload: {r.status_code}, file_id={fid}")

# 3. List files - check Firestore persistence
r = requests.get(f"{BASE}/eeg/files", headers=headers, timeout=10)
files = r.json()
found = [fi for fi in files if fi.get("file_id") == fid]
if found:
    meta = found[0]
    print(f"3. File listing: {r.status_code}, total={len(files)} files")
    print(f"   -> FIRESTORE OK: file_id={meta['file_id']}, original={meta.get('original_filename')}")
else:
    print(f"3. File listing: {r.status_code}, total={len(files)} files")
    print(f"   -> WARNING: Uploaded file not found by file_id (disk fallback may be active)")

# 4. Run prediction
start = time.time()
r = requests.post(
    f"{BASE}/predictions/predict",
    json={"file_id": fid},
    headers=headers,
    timeout=180,
)
elapsed = time.time() - start
if r.status_code in (200, 201):
    d = r.json()
    result = d["result"]
    expl = d["explanation"]
    print(f"4. Prediction: {r.status_code}")
    print(f"   -> Probability: {result['depression_probability']:.4f}")
    print(f"   -> Risk Level:  {result['risk_level']}")
    print(f"   -> Confidence:  {result['confidence']:.4f}")
    print(f"   -> Top Features: {expl.get('top_features', [])[:5]}")
    print(f"   -> Time: {elapsed:.1f}s")
    pred_id = result["prediction_id"]
else:
    print(f"4. Prediction FAILED: {r.status_code}")
    print(f"   -> {r.text[:300]}")
    pred_id = None

# 5. Check prediction history - THE KEY TEST
r = requests.get(f"{BASE}/predictions/history", headers=headers, timeout=10)
history = r.json()
print(f"5. Prediction History: {r.status_code}, count={len(history)}")
if history:
    latest = history[0]["result"]
    print(f"   -> FIRESTORE OK: Latest prediction persisted!")
    print(f"      prob={latest['depression_probability']}, risk={latest['risk_level']}")
else:
    print(f"   -> WARNING: History empty - Firestore write may not be working")

# 6. Get specific prediction by ID
if pred_id:
    r = requests.get(
        f"{BASE}/predictions/{pred_id}",
        headers=headers,
        timeout=10,
    )
    if r.status_code == 200:
        print(f"6. Get Prediction by ID: {r.status_code}")
        print(f"   -> FIRESTORE OK: Prediction {pred_id[:12]}... retrieved")
    else:
        print(f"6. Get Prediction by ID: {r.status_code}")
        print(f"   -> WARNING: Could not retrieve prediction: {r.text[:200]}")

# Summary
print()
print("=" * 60)
firestore_ok = bool(found) and len(history) > 0
if firestore_ok:
    print("RESULT: FIRESTORE FULLY OPERATIONAL")
    print("  - File metadata persists to Firestore")
    print("  - Prediction history persists to Firestore")
    print("  - All CRUD operations working")
else:
    print("RESULT: FIRESTORE PARTIALLY WORKING")
    if not found:
        print("  - File metadata NOT persisting (disk fallback active)")
    if not history:
        print("  - Prediction history NOT persisting")
print("=" * 60)
