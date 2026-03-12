"""
DepreSense E2E API Tests
Tests all backend API endpoints with real Firebase.
"""
import requests
import json
import time
import os
import sys

BASE = "http://localhost:8000"
EMAIL = "depresense.e2e.test@gmail.com"
PW = "Test123!Pass"
NAME = "E2E Test User"
EDF_PATH = r"d:\Study\0. degree\Last Year\DepreSense Project\MDD S33 EC.edf"

results = []
token = None
file_id = None
pred_id = None


def test(name, fn):
    global results
    try:
        ok, detail = fn()
        results.append((name, ok, detail))
        symbol = "PASS" if ok else "FAIL"
        print(f"[{symbol}] {name}: {detail}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"[FAIL] {name}: {e}")
    print()


# ---- Test 1: Health Check ----
def t_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    d = r.json()
    return r.status_code == 200, f"status={r.status_code} body={d}"
test("1. Health Check", t_health)


# ---- Test 2: Firebase Health ----
def t_firebase():
    r = requests.get(f"{BASE}/health/firebase", timeout=10)
    d = r.json()
    return d.get("firebase_connected") is True, f"firebase_connected={d.get('firebase_connected')}"
test("2. Firebase Health", t_firebase)


# ---- Test 3: Model Health ----
def t_model():
    r = requests.get(f"{BASE}/health/model", timeout=10)
    d = r.json()
    return d.get("model_loaded") is True, f"model_loaded={d.get('model_loaded')}"
test("3. Model Health", t_model)


# ---- Test 4: Signup (new user) ----
def t_signup():
    new_email = f"e2e_{int(time.time())}@gmail.com"
    r = requests.post(
        f"{BASE}/auth/signup",
        json={"email": new_email, "password": PW, "name": NAME},
        timeout=20,
    )
    if r.status_code == 201:
        d = r.json()
        return True, f"status=201, email={new_email}, token_len={len(d.get('token', ''))}"
    else:
        d = r.json()
        return False, f"status={r.status_code}, detail={d.get('detail')}"
test("4. Signup (new user)", t_signup)


# ---- Test 5: Login ----
def t_login():
    global token
    r = requests.post(
        f"{BASE}/auth/login",
        json={"email": EMAIL, "password": PW},
        timeout=20,
    )
    if r.status_code == 200:
        d = r.json()
        token = d["token"]
        user = d["user"]
        return True, f"status=200, uid={user['uid']}, email={user['email']}, token_len={len(token)}"
    return False, f"status={r.status_code}, body={r.text[:200]}"
test("5. Login", t_login)


# ---- Test 6: Auth/Me ----
def t_me():
    if not token:
        return False, "No token from login"
    r = requests.get(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 200:
        d = r.json()
        return True, f"uid={d['uid']}, email={d['email']}, name={d.get('name')}"
    return False, f"status={r.status_code}, body={r.text[:200]}"
test("6. Auth/Me (token validation)", t_me)


# ---- Test 7: EEG File Upload ----
def t_upload():
    global file_id
    if not token:
        return False, "No token"
    if not os.path.exists(EDF_PATH):
        return False, f"EDF file not found: {EDF_PATH}"
    with open(EDF_PATH, "rb") as f:
        r = requests.post(
            f"{BASE}/eeg/upload",
            files={"file": ("MDD_S33_EC.edf", f, "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
    if r.status_code in (200, 201):
        d = r.json()
        file_id = d.get("file_id")
        return True, f"status={r.status_code}, file_id={file_id}, filename={d.get('filename')}"
    return False, f"status={r.status_code}, body={r.text[:300]}"
test("7. EEG File Upload", t_upload)


# ---- Test 8: List EEG Files ----
def t_files():
    if not token:
        return False, "No token"
    r = requests.get(
        f"{BASE}/eeg/files",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 200:
        d = r.json()
        return True, f"status=200, {len(d)} file(s)"
    return False, f"status={r.status_code}"
test("8. List EEG Files", t_files)


# ---- Test 9: Run Prediction ----
def t_predict():
    global pred_id
    if not token or not file_id:
        return False, f"Missing token={bool(token)} file_id={file_id}"
    start = time.time()
    r = requests.post(
        f"{BASE}/predictions/predict",
        json={"file_id": file_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    elapsed = time.time() - start
    if r.status_code in (200, 201):
        d = r.json()
        result = d.get("result", {})
        pred_id = result.get("prediction_id")
        prob = result.get("depression_probability")
        risk = result.get("risk_level")
        conf = result.get("confidence")
        expl = d.get("explanation", {})
        tops = expl.get("top_features", [])
        summary = expl.get("explanation_summary", "")[:80]
        return True, (
            f"prob={prob:.4f}, risk={risk}, confidence={conf:.4f}, "
            f"top_features={tops[:5]}, time={elapsed:.1f}s, pred_id={pred_id}"
        )
    return False, f"status={r.status_code}, body={r.text[:300]}, time={elapsed:.1f}s"
test("9. Run Prediction", t_predict)


# ---- Test 10: Prediction History ----
def t_history():
    if not token:
        return False, "No token"
    r = requests.get(
        f"{BASE}/predictions/history",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 200:
        d = r.json()
        return True, f"status=200, {len(d)} prediction(s) in history"
    return False, f"status={r.status_code}, body={r.text[:200]}"
test("10. Prediction History", t_history)


# ---- Test 11: Invalid Login (wrong password) ----
def t_invalid_login():
    r = requests.post(
        f"{BASE}/auth/login",
        json={"email": EMAIL, "password": "wrongpassword"},
        timeout=15,
    )
    if r.status_code == 401:
        msg = r.json().get("detail", {}).get("message", "")
        return True, f"status=401, error_msg='{msg}'"
    return False, f"status={r.status_code}"
test("11. Invalid Login (wrong password)", t_invalid_login)


# ---- Test 12: Invalid File Upload ----
def t_invalid_file():
    if not token:
        return False, "No token"
    r = requests.post(
        f"{BASE}/eeg/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code in (400, 422):
        msg = r.json().get("detail", "")
        if isinstance(msg, dict):
            msg = msg.get("message", "")
        return True, f"status={r.status_code}, correctly rejected: {msg}"
    return False, f"status={r.status_code}, body={r.text[:200]}"
test("12. Invalid File Upload (.txt)", t_invalid_file)


# ---- Test 13: Unauthorized Access ----
def t_no_auth():
    r = requests.get(f"{BASE}/auth/me", timeout=5)
    if r.status_code == 401:
        msg = r.json().get("detail", {})
        if isinstance(msg, dict):
            msg = msg.get("message", "")
        return True, f"status=401, msg='{msg}'"
    return False, f"status={r.status_code}"
test("13. Unauthorized Access (no token)", t_no_auth)


# ---- Test 14: Logout ----
def t_logout():
    if not token:
        return False, "No token"
    r = requests.post(
        f"{BASE}/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code == 200:
        return True, f"status=200, msg='{r.json().get('message')}'"
    return False, f"status={r.status_code}"
test("14. Logout", t_logout)


# ---- Summary ----
print("=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"RESULTS: {passed}/{total} tests passed")
print("=" * 60)

for name, ok, detail in results:
    symbol = "PASS " if ok else "FAIL "
    print(f"  [{symbol}] {name}")

if passed < total:
    print(f"\nFailed tests:")
    for name, ok, detail in results:
        if not ok:
            print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("\nAll tests passed!")
    sys.exit(0)
