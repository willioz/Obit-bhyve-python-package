.PHONY: help install install-dev test test-cov lint format type-check clean build upload-test upload docs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install the package with development dependencies
	pip install -e ".[dev]"

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=orbit_bhyve --cov-report=html --cov-report=term-missing

lint: ## Run linting
	flake8 orbit_bhyve/ tests/ examples/
	mypy orbit_bhyve/

format: ## Format code
	black orbit_bhyve/ tests/ examples/

type-check: ## Run type checking
	mypy orbit_bhyve/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build the package
	python -m build

upload-test: build ## Upload to TestPyPI
	twine upload --repository testpypi dist/*

upload: build ## Upload to PyPI
	twine upload dist/*

docs: ## Build documentation
	sphinx-build -b html docs/ docs/_build/html

check: lint test ## Run all checks (lint + test)

all: clean install-dev check build ## Run everything (clean, install-dev, check, build)
