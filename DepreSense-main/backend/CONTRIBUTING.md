# Contributing to DepreSense Backend

Thank you for your interest in contributing! This guide will help you get started.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **pip** (package manager)
- **Git**
- **Docker** (optional, for containerized development)
- A Firebase project with service account credentials

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/depresense-backend.git
cd depresense-backend/backend

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
.\venv\Scripts\activate         # Windows

# 3. Install dependencies
make install
# or: pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set FIREBASE_CREDENTIALS_PATH, MODEL_PATH, etc.

# 5. Run locally
make run
# Backend available at http://localhost:8000

# 6. Run tests
make test
```

---

## Development Workflow

### 1. Create a feature branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make your changes

- Write code following the [Code Standards](#code-standards)
- Add or update tests as needed
- Update documentation if the API changes

### 3. Run the test suite

```bash
# Run all tests
make test

# Run fast tests only (skip slow/integration)
make test-fast

# Check coverage
make test-coverage
```

### 4. Commit with clear messages

```
feat: add EEG signal quality scoring endpoint
fix: correct SHAP feature importance calculation
docs: update API endpoint table in README
test: add edge case tests for file upload
```

### 5. Push and open a Pull Request

```bash
git push origin feature/your-feature-name
```

---

## Code Standards

### Python Style

- Follow **PEP 8** style guidelines
- Max line length: **88 characters** (Black formatter compatible)
- Use **4 spaces** for indentation (never tabs)

### Type Hints

All function signatures should include type hints:

```python
def determine_risk_level(probability: float) -> str:
    """Map a depression probability to a risk category."""
    if probability >= 0.67:
        return "high"
    elif probability >= 0.33:
        return "medium"
    return "low"
```

### Docstrings

Use descriptive docstrings for all public functions, classes, and modules:

```python
def save_uploaded_file(file: UploadFile, upload_dir: str) -> tuple[str, str]:
    """Save an uploaded file to disk.

    Args:
        file: The uploaded file from the request.
        upload_dir: Directory to save the file to.

    Returns:
        A tuple of (file_id, file_path).

    Raises:
        IOError: If the file cannot be written to disk.
    """
```

### Project Structure

```
app/
├── config.py          # Settings and environment variables
├── main.py            # FastAPI application entry point
├── routes/            # API endpoint handlers
├── schemas/           # Pydantic request/response models
├── services/          # Business logic
├── middleware/        # Request/response processing
├── models/            # ML model loading
└── utils/             # Helper utilities
tests/                 # Test files
```

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `eeg_processor.py` |
| Functions | `snake_case()` | `run_inference()` |
| Classes | `PascalCase` | `PredictionResult` |
| Constants | `UPPER_SNAKE` | `MAX_FILE_SIZE_MB` |
| Test functions | `test_descriptive_name()` | `test_upload_invalid_format()` |

---

## Testing Requirements

### Rules

1. **All new features must have tests** — no exceptions
2. **All bug fixes must include a regression test**
3. **Minimum coverage: 80%** — check with `make test-coverage`
4. **Tests must pass before merging** — CI will enforce this

### Test structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_auth.py             # Authentication tests
├── test_eeg.py              # EEG upload/management tests
├── test_predictions.py      # Prediction endpoint tests
├── test_error_handling.py   # Error response format tests
├── test_services.py         # Service-layer unit tests
├── test_health.py           # Health check tests
└── test_integration.py      # End-to-end workflow tests
```

### Writing tests

```python
class TestUploadEEG:
    """POST /eeg/upload"""

    @patch("app.routes.eeg.firestore_service")
    def test_upload_edf_success(self, mock_fs, test_client, auth_headers):
        # Arrange
        files = {"file": ("test.edf", b"\x00" * 100, "application/octet-stream")}

        # Act
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)

        # Assert
        assert resp.status_code == 201
        assert "file_id" in resp.json()
```

### Running tests

```bash
make test               # All tests
make test-fast          # Skip slow/integration
make test-coverage      # With HTML coverage report

# Run a specific file
pytest tests/test_auth.py -v

# Run a specific test
pytest tests/test_auth.py::TestSignup::test_signup_success -v
```

---

## Pull Request Process

### Before submitting

- [ ] All tests pass (`make test`)
- [ ] Coverage ≥ 80% (`make test-coverage`)
- [ ] Code follows PEP 8 style
- [ ] Docstrings added for new public functions
- [ ] README updated if API changes
- [ ] No sensitive data in code or commits

### PR description template

```markdown
## What

Brief description of the change.

## Why

Context / motivation / issue reference.

## How

Technical approach taken.

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Screenshots (if applicable)
```

### Review process

1. Open a PR against `main` branch
2. Request review from at least one team member
3. Address review comments
4. Ensure CI passes
5. Merge after approval

---

## Reporting Bugs

### Bug report template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To reproduce**
1. Start the backend with `make run`
2. Send request: `curl -X POST http://localhost:8000/...`
3. Observe error

**Expected behavior**
What should happen.

**Actual behavior**
What actually happens.

**Logs**
Include relevant logs from `logs/depresense.log`:
```
paste log output here
```

**Environment**
- OS: Windows 11 / Ubuntu 22.04 / macOS Ventura
- Python version: 3.11.x
- Backend version: git commit hash

**Additional context**
Anything else relevant.
```

### How to provide logs

```bash
# View the last 50 lines of the log
tail -n 50 logs/depresense.log

# Windows PowerShell
Get-Content logs/depresense.log -Tail 50

# Search for errors
grep -i error logs/depresense.log
```

---

## Questions?

Open a discussion or issue on the repository. We're happy to help!
