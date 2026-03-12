"""Quick E2E smoke test — no emoji, clean output."""
import requests
import json
import time
import os
import sys

# Force flush on every print
_builtin_print = print
def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _builtin_print(*args, **kwargs)

BASE = "http://localhost:8000"
EMAIL = f"e2e_{int(time.time())}@depresense.com"
PASSWORD = "TestPass123!"
EDF_PATH = r"D:\Study\0. degree\Last Year\DepreSense Project\MDD S33 EC.edf"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_results.log")

# Also write to log file
log_fh = open(LOG_FILE, "w", encoding="utf-8")
_print2 = print
def print(*args, **kwargs):
    kwargs.pop("file", None)
    _print2(*args, **kwargs)
    _builtin_print(*args, file=log_fh, flush=True)

def section(title):
    print(f"\n--- {title} ---")

# Phase 1: Health
section("Health")
h1 = requests.get(f"{BASE}/health").json()
h2 = requests.get(f"{BASE}/health/model").json()
h3 = requests.get(f"{BASE}/health/firebase").json()
print(f"  API: {h1['status']} v{h1['version']}")
print(f"  Model: loaded={h2['model_loaded']}")
print(f"  Firebase: connected={h3['firebase_connected']}")

# Phase 2: Signup
section("Signup")
r = requests.post(f"{BASE}/auth/signup", json={"email": EMAIL, "password": PASSWORD, "name": "Test User"})
print(f"  Status: {r.status_code}")
d = r.json()
token = ""
if r.status_code == 201:
    uid = d["user"]["uid"]
    token = d["token"]
    print(f"  uid={uid[:12]}...  email={d['user']['email']}")
    print(f"  PASS")
elif r.status_code in (409, 401) or "exist" in str(d).lower():
    print(f"  User may already exist, will try login")
    print(f"  SKIP (expected for repeat runs)")
else:
    print(f"  FAIL: {d}")

# Phase 3: Login
section("Login")
r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
print(f"  Status: {r.status_code}")
d = r.json()
if r.status_code == 200:
    token = d["token"]
    print(f"  token={token[:20]}...")
    print(f"  PASS")
else:
    print(f"  FAIL: {d}")

# Phase 4: Token validation
section("Token Validation (/auth/me)")
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    me = r.json()
    print(f"  uid={me.get('uid', '?')[:12]}...")
    print(f"  PASS")
else:
    print(f"  FAIL: {r.json()}")

# Bad token
r2 = requests.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer bad_token_123"})
print(f"  Bad token -> {r2.status_code} {'PASS' if r2.status_code == 401 else 'FAIL'}")

# Phase 5: Upload EDF
section("EEG Upload")
file_id = ""
if os.path.exists(EDF_PATH):
    print(f"  File: {os.path.basename(EDF_PATH)} ({os.path.getsize(EDF_PATH)} bytes)")
    with open(EDF_PATH, "rb") as f:
        r = requests.post(
            f"{BASE}/eeg/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("MDD_S33_EC.edf", f, "application/octet-stream")},
        )
    print(f"  Status: {r.status_code}")
    d = r.json()
    if r.status_code == 201:
        file_id = d["file_id"]
        print(f"  file_id={file_id}")
        print(f"  PASS")
    else:
        print(f"  FAIL: {d}")
else:
    print(f"  File not found: {EDF_PATH}")
    print(f"  SKIP")

# Phase 6: File listing
section("File Listing")
r = requests.get(f"{BASE}/eeg/files", headers={"Authorization": f"Bearer {token}"})
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    files = r.json()
    print(f"  Files: {len(files)}")
    print(f"  PASS")
else:
    print(f"  FAIL: {r.json()}")

# Phase 7: Prediction
section("Prediction")
pred_id = ""
if file_id:
    r = requests.post(
        f"{BASE}/predictions/predict",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"file_id": file_id},
        timeout=120,
    )
    print(f"  Status: {r.status_code}")
    d = r.json()
    if r.status_code == 201:
        res = d["result"]
        exp = d.get("explanation", {})
        print(f"  Probability: {res['depression_probability']:.3f}")
        print(f"  Risk level:  {res['risk_level']}")
        print(f"  Confidence:  {res['confidence']:.3f}")
        print(f"  Top features: {exp.get('top_features', [])[:5]}")
        pred_id = res["prediction_id"]
        print(f"  PASS")
    else:
        print(f"  FAIL: {d}")
else:
    print(f"  SKIP (no file_id)")

# Phase 8: History
section("Prediction History")
r = requests.get(f"{BASE}/predictions/history", headers={"Authorization": f"Bearer {token}"})
print(f"  Status: {r.status_code}")
if r.status_code == 200:
    preds = r.json()
    print(f"  Total predictions: {len(preds)}")
    if pred_id:
        found = any(p["result"]["prediction_id"] == pred_id for p in preds)
        print(f"  Latest prediction found: {found}")
    print(f"  PASS")
else:
    print(f"  FAIL: {r.json()}")

# Phase 9: Logout
section("Logout")
r = requests.post(f"{BASE}/auth/logout", headers={"Authorization": f"Bearer {token}"})
print(f"  Status: {r.status_code}")
print(f"  {'PASS' if r.status_code == 200 else 'FAIL'}")

print("\n" + "=" * 50)
print("  ALL TESTS COMPLETE")
print("=" * 50)
