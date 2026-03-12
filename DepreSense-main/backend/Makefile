# ──────────────────────────────────────────────────────────────
#  DepreSense Backend — Development Commands
# ──────────────────────────────────────────────────────────────

.PHONY: help install run run-docker stop clean test test-fast test-coverage logs

## Show this help message
help:
	@echo.
	@echo   DepreSense Backend - available commands
	@echo   ───────────────────────────────────────
	@echo   make install        Install Python dependencies
	@echo   make run            Run backend locally (hot-reload)
	@echo   make run-docker     Run backend in Docker
	@echo   make stop           Stop Docker containers
	@echo   make clean          Remove caches and temp files
	@echo   make test           Run full test suite
	@echo   make test-fast      Run tests excluding slow/integration
	@echo   make test-coverage  Run tests with HTML coverage report
	@echo   make logs           Tail Docker logs
	@echo.

## Install Python dependencies from requirements.txt
install:
	pip install -r requirements.txt

## Run backend locally with hot-reload
run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## Run backend in Docker (foreground)
run-docker:
	docker-compose up --build

## Stop Docker containers
stop:
	docker-compose down

## Remove caches and temp files
clean:
	@echo Cleaning caches...
	@if exist __pycache__ rd /s /q __pycache__
	@if exist .pytest_cache rd /s /q .pytest_cache
	@if exist htmlcov rd /s /q htmlcov
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	@del /s /q *.pyc 2>nul
	@echo Done.

## Run full test suite
test:
	pytest tests/ -v

## Run fast tests only (skip slow and integration)
test-fast:
	pytest tests/ -v -m "not slow and not integration"

## Run tests with HTML coverage report
test-coverage:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

## Tail Docker container logs
logs:
	docker-compose logs -f backend
