.PHONY: install install-dev install-all lint format typecheck test test-all test-integration test-coverage clean build publish docs run-api run-dashboard run-cli docker-build docker-up pre-commit security audit

SHELL := /bin/bash
VENV := .venv
PYTHON := python3
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest
PLAYWRIGHT := $(VENV)/bin/playwright

# ─── Installation ────────────────────────────────────────────────────────────

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e "."
	$(PLAYWRIGHT) install chromium

install-dev: install
	$(PIP) install -e ".[dev]"

install-all: install-dev
	$(PIP) install -e ".[all]"

# ─── Quality ─────────────────────────────────────────────────────────────────

lint:
	$(RUFF) check src/ tests/ examples/
	$(RUFF) format --check src/ tests/ examples/

format:
	$(RUFF) format src/ tests/ examples/
	$(RUFF) check --fix src/ tests/ examples/

typecheck:
	$(MYPY) src/computeforge/ --ignore-missing-imports

security:
	$(PIP) install bandit 2>/dev/null; $(VENV)/bin/bandit -r src/computeforge/ -s B101,B311,B404,B603,B607

audit:
	$(PIP) install pip-audit 2>/dev/null; $(VENV)/bin/pip-audit

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v --ignore=tests/test_core/test_engine.py -k "not integration" --cov=src/computeforge --cov-report=term --cov-report=html

test-all:
	$(PYTEST) tests/ -v --cov=src/computeforge --cov-report=term --cov-report=html

test-integration:
	$(PYTEST) tests/test_core/test_engine.py -v

test-coverage:
	$(PYTEST) tests/ -v --cov=src/computeforge --cov-report=term --cov-report=html --cov-fail-under=80

test-quick:
	$(PYTEST) tests/ -v --ignore=tests/test_core/test_engine.py -k "not integration" -x

# ─── Build & Publish ─────────────────────────────────────────────────────────

build: clean
	$(PYTHON) -m build

publish: build
	$(PIP) install twine
	$(PYTHON) -m twine upload dist/*

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# ─── Run ─────────────────────────────────────────────────────────────────────

run-api:
	$(VENV)/bin/uvicorn computeforge.api.server:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	$(VENV)/bin/python -c "from computeforge.dashboard.app import launch_dashboard; launch_dashboard(host='0.0.0.0', port=7860)"

run-cli:
	$(VENV)/bin/python -m computeforge.cli.app $(filter-out $@,$(MAKECMDGOALS))

# ─── Docker ──────────────────────────────────────────────────────────────────

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

# ─── Pre-commit ──────────────────────────────────────────────────────────────

pre-commit:
	$(PIP) install pre-commit 2>/dev/null
	$(VENV)/bin/pre-commit install
	$(VENV)/bin/pre-commit run --all-files

# ─── Help ────────────────────────────────────────────────────────────────────

help:
	@echo "ComputeForge Development Makefile"
	@echo "================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install       Create venv, install package + Playwright"
	@echo "  make install-dev   Install with dev dependencies"
	@echo "  make install-all   Install everything"
	@echo ""
	@echo "Quality:"
	@echo "  make lint          Ruff lint + format check"
	@echo "  make format        Auto-format code"
	@echo "  make typecheck     MyPy type checking"
	@echo "  make security      Bandit security scan"
	@echo "  make audit         Pip audit dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run unit tests"
	@echo "  make test-all      Run all tests"
	@echo "  make test-integration  Run browser integration tests"
	@echo "  make test-coverage Run with coverage threshold"
	@echo ""
	@echo "Build:"
	@echo "  make build         Build distribution packages"
	@echo "  make publish       Upload to PyPI"
	@echo "  make clean         Remove build artifacts"
	@echo ""
	@echo "Run:"
	@echo "  make run-api       Start FastAPI server"
	@echo "  make run-dashboard Start Gradio dashboard"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker images"
	@echo "  make docker-up     Start Docker services"
