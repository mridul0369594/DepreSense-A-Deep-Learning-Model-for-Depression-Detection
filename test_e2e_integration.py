"""
DepreSense End-to-End Integration Test Script
==============================================
Tests the full API flow from the frontend's perspective:
  1. Health checks
  2. Signup  → creates user in Firebase
  3. Login   → gets token
  4. Token validation (/auth/me)
  5. EEG upload  → POST /eeg/upload
  6. File listing → GET /eeg/files
  7. Prediction   → POST /predictions/predict
  8. Prediction history → GET /predictions/history
  9. Logout  → POST /auth/logout
 10. Invalid token handling

Usage:
    py -3.11 test_e2e_integration.py

Each test prints PASS/FAIL and a summary at the end.
"""

import json
import os
import sys
import time
from pathlib import Path

# Try to use requests if available, otherwise fall back to urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ── Helpers ────────────────────────────────────────────────

results = []


def log_result(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    results.append((name, passed, detail))


def api_get(path: str, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if HAS_REQUESTS:
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.status_code, resp.json() if resp.text else {}
    else:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read()) if e.read() else {}


def api_post(path: str, body: dict | None = None, token: str | None = None,
             files: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if HAS_REQUESTS:
        if files:
            resp = requests.post(url, headers=headers, files=files, timeout=60)
        else:
            headers["Content-Type"] = "application/json"
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, {"raw": resp.text}
    else:
        data = json.dumps(body or {}).encode()
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.read() else ""
            return e.code, json.loads(body_text) if body_text else {}


def api_delete(path: str, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if HAS_REQUESTS:
        resp = requests.delete(url, headers=headers, timeout=30)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, {}
    else:
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, {}


# ── Tests ──────────────────────────────────────────────────

def test_health():
    print("\n── Phase 1: Health Checks ──────────────────────")
    code, body = api_get("/health")
    log_result("GET /health", code == 200, f"status={body.get('status')}, version={body.get('version')}")

    code, body = api_get("/health/model")
    log_result("GET /health/model", code == 200, f"model_loaded={body.get('model_loaded')}")

    code, body = api_get("/health/firebase")
    firebase_ok = code == 200
    firebase_connected = body.get("firebase_connected", False)
    log_result("GET /health/firebase", firebase_ok, f"connected={firebase_connected}")

    return firebase_connected


def test_signup(email: str, password: str, name: str) -> tuple[bool, str]:
    print("\n── Phase 2: Signup ─────────────────────────────")
    code, body = api_post("/auth/signup", {"email": email, "password": password, "name": name})

    if code == 201:
        token = body.get("token", "")
        user = body.get("user", {})
        log_result("POST /auth/signup", True,
                   f"uid={user.get('uid', '?')[:12]}..., email={user.get('email')}")
        return True, token
    else:
        error_detail = body.get("detail", {})
        error_code = error_detail.get("code", "?") if isinstance(error_detail, dict) else str(error_detail)
        error_msg = error_detail.get("message", "") if isinstance(error_detail, dict) else ""
        log_result("POST /auth/signup", False, f"HTTP {code}: {error_code} — {error_msg}")
        return False, ""


def test_login(email: str, password: str) -> tuple[bool, str]:
    print("\n── Phase 3: Login ──────────────────────────────")
    code, body = api_post("/auth/login", {"email": email, "password": password})

    if code == 200:
        token = body.get("token", "")
        user = body.get("user", {})
        log_result("POST /auth/login", True,
                   f"uid={user.get('uid', '?')[:12]}..., email={user.get('email')}")
        return True, token
    else:
        error_detail = body.get("detail", {})
        error_code = error_detail.get("code", "?") if isinstance(error_detail, dict) else str(error_detail)
        error_msg = error_detail.get("message", "") if isinstance(error_detail, dict) else ""
        log_result("POST /auth/login", False, f"HTTP {code}: {error_code} — {error_msg}")
        return False, ""


def test_token_validation(token: str):
    print("\n── Phase 4: Token Validation ───────────────────")
    code, body = api_get("/auth/me", token=token)
    if code == 200:
        log_result("GET /auth/me", True, f"uid={body.get('uid', '?')[:12]}...")
    else:
        log_result("GET /auth/me", False, f"HTTP {code}")

    # Invalid token
    code, _ = api_get("/auth/me", token="invalidtoken123")
    log_result("GET /auth/me (bad token)", code == 401, f"HTTP {code}")


def test_eeg_upload(token: str) -> str | None:
    print("\n── Phase 5: EEG Upload ─────────────────────────")

    # Find a .edf file for testing
    edf_paths = [
        Path(__file__).parent / "DepreSense-main" / "backend" / "uploads",
        Path(__file__).parent / "DepreSense-main" / "data",
        Path(__file__).parent,
    ]

    edf_file = None
    for base in edf_paths:
        if base.exists():
            for f in base.rglob("*.edf"):
                edf_file = f
                break
        if edf_file:
            break

    if not edf_file:
        log_result("EEG Upload", False, "No .edf test file found")
        return None

    if HAS_REQUESTS:
        with open(edf_file, "rb") as f:
            code, body = api_post("/eeg/upload", token=token,
                                  files={"file": (edf_file.name, f, "application/octet-stream")})
    else:
        log_result("EEG Upload", False, "Requires `requests` library for file upload")
        return None

    if code == 201:
        file_id = body.get("file_id", "")
        log_result("POST /eeg/upload", True, f"file_id={file_id}")
        return file_id
    else:
        error_detail = body.get("detail", {})
        error_code = error_detail.get("code", "?") if isinstance(error_detail, dict) else str(error_detail)
        log_result("POST /eeg/upload", False, f"HTTP {code}: {error_code}")
        return None


def test_file_listing(token: str, expected_file_id: str | None):
    print("\n── Phase 6: File Listing ───────────────────────")
    code, body = api_get("/eeg/files", token=token)
    if code == 200:
        file_ids = [f.get("file_id") for f in body] if isinstance(body, list) else []
        found = expected_file_id in file_ids if expected_file_id else True
        log_result("GET /eeg/files", True,
                   f"{len(file_ids)} files, expected_file_found={found}")
    else:
        log_result("GET /eeg/files", False, f"HTTP {code}")


def test_prediction(token: str, file_id: str) -> str | None:
    print("\n── Phase 7: Prediction ─────────────────────────")
    code, body = api_post("/predictions/predict", {"file_id": file_id}, token=token)

    if code == 201:
        result = body.get("result", {})
        explanation = body.get("explanation", {})
        pred_id = result.get("prediction_id", "")
        prob = result.get("depression_probability", 0)
        risk = result.get("risk_level", "?")
        conf = result.get("confidence", 0)
        top = explanation.get("top_features", [])
        log_result("POST /predictions/predict", True,
                   f"prob={prob:.3f}, risk={risk}, confidence={conf:.3f}")
        log_result("  SHAP explanation", len(top) > 0,
                   f"top_features={top[:5]}")
        return pred_id
    else:
        error_detail = body.get("detail", {})
        error_code = error_detail.get("code", "?") if isinstance(error_detail, dict) else str(error_detail)
        error_msg = error_detail.get("message", "") if isinstance(error_detail, dict) else ""
        log_result("POST /predictions/predict", False,
                   f"HTTP {code}: {error_code} — {error_msg}")
        return None


def test_prediction_history(token: str, expected_pred_id: str | None):
    print("\n── Phase 8: Prediction History ─────────────────")
    code, body = api_get("/predictions/history", token=token)
    if code == 200 and isinstance(body, list):
        pred_ids = [p.get("result", {}).get("prediction_id") for p in body]
        found = expected_pred_id in pred_ids if expected_pred_id else True
        log_result("GET /predictions/history", True,
                   f"{len(pred_ids)} predictions, expected_found={found}")
    else:
        log_result("GET /predictions/history", False, f"HTTP {code}")


def test_logout(token: str):
    print("\n── Phase 9: Logout ─────────────────────────────")
    code, body = api_post("/auth/logout", token=token)
    log_result("POST /auth/logout", code == 200, f"message={body.get('message', '?')}")

    # Verify token is revoked
    code2, _ = api_get("/auth/me", token=token)
    log_result("GET /auth/me (after logout)", code2 == 401,
               f"HTTP {code2} (expected 401)")


# ── Main ───────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  DepreSense E2E Integration Tests")
    print(f"  Backend: {BASE_URL}")
    print(f"  Time:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Phase 1: Health
    firebase_connected = test_health()

    if not firebase_connected:
        print("\n" + "=" * 60)
        print("⚠️  Firebase is NOT connected.")
        print("   Auth/EEG/Prediction tests will be skipped.")
        print("   To enable full testing:")
        print("   1. Create config/firebase-service-account.json")
        print("   2. Set FIREBASE_API_KEY in .env")
        print("   3. Restart the backend")
        print("=" * 60)

        # Still test CORS
        print("\n── Bonus: CORS Check ──────────────────────────")
        if HAS_REQUESTS:
            resp = requests.options(
                f"{BASE_URL}/auth/login",
                headers={
                    "Origin": "http://localhost:8080",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
                timeout=5,
            )
            cors_origin = resp.headers.get("access-control-allow-origin", "")
            log_result("CORS preflight", cors_origin == "http://localhost:8080",
                       f"allow-origin={cors_origin}")
        else:
            log_result("CORS preflight", False, "Requires `requests` library")
    else:
        # Full test suite
        test_email = f"e2e_test_{int(time.time())}@depresense.com"
        test_password = "TestPass123!"
        test_name = "E2E Test User"

        # Phase 2: Signup
        signup_ok, token = test_signup(test_email, test_password, test_name)

        if not signup_ok:
            # Try login in case user already exists
            login_ok, token = test_login(test_email, test_password)
            if not login_ok:
                print("\n❌ Cannot authenticate — aborting remaining tests.")
                return print_summary()
        else:
            # Phase 3: Login with the same credentials
            login_ok, token2 = test_login(test_email, test_password)
            if login_ok:
                token = token2  # Use the latest token

        # Phase 4: Token validation
        test_token_validation(token)

        # Phase 5: EEG upload
        file_id = test_eeg_upload(token)

        # Phase 6: File listing
        test_file_listing(token, file_id)

        # Phase 7: Prediction
        pred_id = None
        if file_id:
            pred_id = test_prediction(token, file_id)

        # Phase 8: Prediction history
        test_prediction_history(token, pred_id)

        # Phase 9: Logout
        test_logout(token)

    print_summary()


def print_summary():
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed
    print(f"  SUMMARY: {passed}/{total} passed, {failed} failed")

    if failed > 0:
        print("\n  Failed tests:")
        for name, p, detail in results:
            if not p:
                print(f"    ❌ {name}: {detail}")

    print("=" * 60)


if __name__ == "__main__":
    main()
