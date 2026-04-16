PYTHON  := python3
VENV    := .venv
BIN     := $(VENV)/bin

.PHONY: install install-docs format lint typecheck pylint test check docs docs-serve clean distclean help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Create .venv and install package with dev dependencies
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev,fuse]"

install-docs: ## Install documentation dependencies into .venv
	$(BIN)/pip install -e ".[docs]"

format: ## Auto-format with ruff
	$(BIN)/ruff format wadlib tests
	$(BIN)/ruff check --fix wadlib tests

lint: ## Run ruff linter
	$(BIN)/ruff check wadlib tests

typecheck: ## Run mypy strict type checking
	$(BIN)/mypy wadlib

pylint: ## Run pylint
	$(BIN)/pylint wadlib

test: ## Run pytest with coverage
	$(BIN)/pytest --durations=15

check: format lint typecheck pylint test ## Run all checks

docs: ## Build documentation site (output: site/)
	$(BIN)/mkdocs build --strict

docs-serve: ## Serve documentation locally at http://127.0.0.1:8000
	$(BIN)/mkdocs serve

clean: ## Remove caches and build artifacts
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

distclean: clean ## Remove everything including .venv
	rm -rf $(VENV)
