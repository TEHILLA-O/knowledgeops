.PHONY: install install-dev test test-unit test-integration test-e2e lint format typecheck docker-build docker-up docker-down demo migrate benchmark evaluate setup status clean

PYTHON ?= python
PIP ?= pip

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-unit:
	$(PYTHON) -m pytest tests/unit/ -v --tb=short

test-integration:
	$(PYTHON) -m pytest tests/integration/ -v --tb=short -m integration

test-e2e:
	$(PYTHON) -m pytest tests/e2e/ -v --tb=short -m e2e

lint:
	$(PYTHON) -m ruff check app tests scripts migrations

format:
	$(PYTHON) -m ruff check --fix app tests scripts migrations
	$(PYTHON) -m ruff format app tests scripts migrations

typecheck:
	$(PYTHON) -m mypy app

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

demo:
	$(PYTHON) scripts/setup_demo.py
	$(PYTHON) scripts/run_case_study_demo.py

migrate:
	$(PYTHON) -m alembic upgrade head

benchmark:
	$(PYTHON) scripts/benchmark_rag.py

evaluate:
	$(PYTHON) scripts/run_evaluation.py

setup:
	$(PYTHON) scripts/setup_demo.py

status:
	knowledgeops status

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
