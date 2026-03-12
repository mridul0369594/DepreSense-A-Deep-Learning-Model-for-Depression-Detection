"""
DepreSense Backend — Full Verification Script
Runs all endpoint tests and prints a summary report.
Output is written to verify_results.txt.
"""

import json
import sys
import time
import urllib.error
import urllib.request
import io

BASE = "http://127.0.0.1:8000"
RESULTS = {}
TOKEN = None
FILE_ID = None
PREDICTION_ID = None

# Capture output to file
out_lines = []

def log(msg=""):
    out_lines.append(msg)
    try:
        print(msg)
    except Exception:
        pass


def req(method, path, body=None, headers=None):
    url = f"{BASE}{path}"
    hdrs = headers or {}
    data = json.dumps(body).encode() if body else None
    if body and "Content-Type" not in hdrs:
        hdrs["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(r)
        raw = resp.read().decode()
        return resp.status, json.loads(raw) if raw else {}, resp
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            d = json.loads(raw)
        except Exception:
            d = {"raw": raw[:200]}
        return e.code, d, e


def ok(label, passed, detail=""):
    sym = "PASS" if passed else "FAIL"
    RESULTS[label] = passed
    log(f"  [{sym}] {label}" + (f"  -- {detail}" if detail else ""))
    return passed


def section(title):
    log(f"\n{'='*60}")
    log(f"  {title}")
    log(f"{'='*60}")


# ================================================================
#  TASK 2: Health Checks
# ================================================================
section("TASK 2: Health Checks")

s, d, _ = req("GET", "/")
ok("GET /", s == 200, f"{s} {d}")

s, d, _ = req("GET", "/health")
ok("GET /health", s == 200 and d.get("status") == "ok", f"{s} {d}")

s, d, _ = req("GET", "/health/model")
model_loaded = d.get("model_loaded", False)
ok("GET /health/model", s == 200, f"{s} model_loaded={model_loaded}")

s, d, _ = req("GET", "/health/firebase")
fb_connected = d.get("firebase_connected", False)
ok("GET /health/firebase", s == 200, f"{s} firebase_connected={fb_connected}")


# ================================================================
#  TASK 3: Authentication Flow
# ================================================================
section("TASK 3: Authentication Flow")

test_email = f"verify_{int(time.time())}@test.com"
s, d, _ = req("POST", "/auth/signup", {
    "email": test_email,
    "password": "TestPassword123!",
    "name": "Verify User",
})
signup_ok = s == 201 and "token" in d
if signup_ok:
    TOKEN = d["token"]
    uid = d.get("user", {}).get("uid", "?")
    ok("POST /auth/signup", True, f"uid={uid[:12]}...")
else:
    ok("POST /auth/signup", False, f"{s} {json.dumps(d)[:120]}")

# Login
if signup_ok:
    s, d, _ = req("POST", "/auth/login", {
        "email": test_email,
        "password": "TestPassword123!",
    })
    login_ok = s == 200 and "token" in d
    if login_ok:
        TOKEN = d["token"]  # refresh token
        ok("POST /auth/login", True, "token refreshed")
    else:
        ok("POST /auth/login", False, f"{s}")
else:
    ok("POST /auth/login", False, "Skipped (signup failed)")

# /auth/me
if TOKEN:
    s, d, _ = req("GET", "/auth/me", headers={
        "Authorization": f"Bearer {TOKEN}"
    })
    ok("GET /auth/me", s == 200 and "uid" in d, f"{s} email={d.get('email','?')}")
else:
    ok("GET /auth/me", False, "No token available")


# ================================================================
#  TASK 4: EEG File Upload
# ================================================================
section("TASK 4: EEG File Upload")

if TOKEN:
    import glob, os

    edf_patterns = [
        "d:/Study/0. degree/Last Year/DepreSense Project/DepreSense-main/data/**/*.edf",
        "d:/Study/0. degree/Last Year/DepreSense Project/DepreSense-main/**/*.edf",
    ]
    edf_file = None
    for pattern in edf_patterns:
        files = glob.glob(pattern, recursive=True)
        if files:
            files.sort(key=os.path.getsize)
            edf_file = files[0]
            break

    if edf_file:
        log(f"  Using EDF: {os.path.basename(edf_file)} ({os.path.getsize(edf_file)//1024} KB)")

        boundary = "----VerifyBoundary12345"
        filename = os.path.basename(edf_file)
        with open(edf_file, "rb") as f:
            file_data = f.read()

        body_parts = []
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
        body_parts.append(b"Content-Type: application/octet-stream")
        body_parts.append(b"")
        body_parts.append(file_data)
        body_parts.append(f"--{boundary}--".encode())
        mp_body = b"\r\n".join(body_parts)

        r = urllib.request.Request(
            f"{BASE}/eeg/upload",
            data=mp_body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(r)
            raw = resp.read().decode()
            s = resp.status
            d = json.loads(raw)
        except urllib.error.HTTPError as e:
            s = e.code
            raw = e.read().decode()
            try:
                d = json.loads(raw)
            except Exception:
                d = {"raw": raw[:200]}

        upload_ok = s == 201 and "file_id" in d
        if upload_ok:
            FILE_ID = d["file_id"]
            ok("POST /eeg/upload", True, f"file_id={FILE_ID[:12]}...")
        else:
            ok("POST /eeg/upload", False, f"{s} {json.dumps(d)[:120]}")

        # List files
        if FILE_ID:
            s, d, _ = req("GET", "/eeg/files", headers={
                "Authorization": f"Bearer {TOKEN}"
            })
            count = len(d) if isinstance(d, list) else "?"
            ok("GET /eeg/files", s == 200 and isinstance(d, list), f"{s} count={count}")

            # Get specific file
            s, d, _ = req("GET", f"/eeg/files/{FILE_ID}", headers={
                "Authorization": f"Bearer {TOKEN}"
            })
            ok("GET /eeg/files/{id}", s == 200, f"{s}")
        else:
            ok("GET /eeg/files", False, "Skipped (upload failed)")
            ok("GET /eeg/files/{id}", False, "Skipped")
    else:
        ok("POST /eeg/upload", False, "No .edf file found on disk")
        ok("GET /eeg/files", False, "Skipped")
        ok("GET /eeg/files/{id}", False, "Skipped")
else:
    ok("POST /eeg/upload", False, "No token")
    ok("GET /eeg/files", False, "Skipped")
    ok("GET /eeg/files/{id}", False, "Skipped")


# ================================================================
#  TASK 5: Predictions
# ================================================================
section("TASK 5: Predictions")

if TOKEN and FILE_ID and model_loaded:
    log("  Running prediction (this may take 10-30s)...")
    s, d, _ = req("POST", "/predictions/predict", {"file_id": FILE_ID}, headers={
        "Authorization": f"Bearer {TOKEN}",
    })
    if s == 201:
        result = d.get("result", {})
        PREDICTION_ID = result.get("prediction_id")
        prob = result.get("depression_probability", "?")
        risk = result.get("risk_level", "?")
        conf = result.get("confidence", "?")
        explanation = d.get("explanation", {})
        top = explanation.get("top_features", [])
        summary = explanation.get("explanation_summary", "")[:60]
        ok("POST /predictions/predict", True,
           f"prob={prob} risk={risk} conf={conf}")
        log(f"    top_features: {top[:5]}")
        log(f"    summary: {summary}...")
    else:
        ok("POST /predictions/predict", False, f"{s} {json.dumps(d)[:150]}")

    # History
    s, d, _ = req("GET", "/predictions/history", headers={
        "Authorization": f"Bearer {TOKEN}"
    })
    count = len(d) if isinstance(d, list) else "?"
    ok("GET /predictions/history", s == 200 and isinstance(d, list), f"{s} count={count}")

    # Specific prediction
    if PREDICTION_ID:
        s, d, _ = req("GET", f"/predictions/{PREDICTION_ID}", headers={
            "Authorization": f"Bearer {TOKEN}"
        })
        ok("GET /predictions/{id}", s == 200, f"{s}")
    else:
        ok("GET /predictions/{id}", False, "No prediction_id")
elif not model_loaded:
    ok("POST /predictions/predict", False, "Model not loaded -- check MODEL_PATH")
    ok("GET /predictions/history", False, "Skipped")
    ok("GET /predictions/{id}", False, "Skipped")
else:
    reason = "No token" if not TOKEN else "No file_id"
    ok("POST /predictions/predict", False, reason)
    ok("GET /predictions/history", False, "Skipped")
    ok("GET /predictions/{id}", False, "Skipped")


# ================================================================
#  TASK 6: Error Handling
# ================================================================
section("TASK 6: Error Handling")

# Missing auth
s, d, _ = req("GET", "/auth/me")
ok("401 -- Missing token", s == 401, f"{s}")

# 404
if TOKEN:
    s, d, _ = req("GET", "/eeg/files/nonexistent-id-xyz", headers={
        "Authorization": f"Bearer {TOKEN}"
    })
    ok("404 -- File not found", s == 404, f"{s}")

    err = d.get("detail", d.get("error", {}))
    has_code = "code" in err if isinstance(err, dict) else False
    ok("Error response has code field", has_code, f"{json.dumps(d)[:100]}")
else:
    ok("404 -- File not found", False, "Skipped")
    ok("Error response has code field", False, "Skipped")

# X-Request-ID
resp = urllib.request.urlopen(f"{BASE}/health")
rid = resp.headers.get("x-request-id", "")
ok("X-Request-ID header present", len(rid) == 32, f"len={len(rid)}")


# ================================================================
#  TASK 7: Firestore
# ================================================================
section("TASK 7: Firestore")

if fb_connected:
    ok("Firebase connected", True, "Check Firestore console for data")
else:
    ok("Firebase connected", False,
       "Credentials not configured -- data NOT persisted to Firestore")
    log("    -> Set FIREBASE_CREDENTIALS_PATH in .env to enable")


# ================================================================
#  SUMMARY
# ================================================================
section("TEST SUMMARY REPORT")

total = len(RESULTS)
passed = sum(1 for v in RESULTS.values() if v)
failed = total - passed

for label, v in RESULTS.items():
    sym = "[OK]  " if v else "[FAIL]"
    log(f"  {sym}  {label}")

log(f"\n  {'='*40}")
log(f"  Total: {total}   Passed: {passed}   Failed: {failed}")

if failed == 0:
    log("  ALL TESTS PASSED -- Backend is fully operational!")
else:
    log(f"  {failed} test(s) need attention")

log(f"  {'='*40}")

# Write to file
with open("verify_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
    f.write("\n")

log("\n  Results saved to verify_results.txt")
