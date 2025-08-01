# Set the python command
python := "uv run python"

# Linting and formatting commands

# Run ruff linter with fixes
lint:
    ruff check --fix --unsafe-fixes .

# Run ruff formatter
format:
    ruff format .

# Run both lint and format
lint-format: lint format

# Check without making changes
check:
    ruff check .
    ruff format --check .

# Run type checking with ty
typecheck:
    {{python}} -m ty check src/textual_mcp/

# Run ty on specific file or directory
typecheck-file path:
    {{python}} -m ty check {{path}}

# Run all checks (lint, format, and type checking)
check-all: check typecheck

# Run tests with coverage
test:
    {{python}} -m pytest tests/ -v --cov=textual_mcp --cov-report=term-missing

# Run tests with coverage and generate HTML report
test-cov:
    {{python}} -m pytest tests/ -v --cov=textual_mcp --cov-report=term-missing --cov-report=html

# Run tests matching a pattern
test-match pattern:
    {{python}} -m pytest tests/ -v -k "{{pattern}}" --cov=textual_mcp --cov-report=term-missing

# Run a specific test file
test-file file:
    {{python}} -m pytest {{file}} -v --cov=textual_mcp --cov-report=term-missing

# Run tests with minimal output
test-quiet:
    {{python}} -m pytest tests/ -q --cov=textual_mcp --cov-report=term-missing

# Run only fast tests (exclude slow/integration tests if marked)
test-fast:
    {{python}} -m pytest tests/ -v -m "not slow" --cov=textual_mcp --cov-report=term-missing

# Clean test artifacts
clean-test:
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf coverage.xml

# Pre-commit commands

# Install pre-commit hooks
pre-commit-install:
    uv run pre-commit install

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Run pre-commit on specific files
pre-commit-files *files:
    uv run pre-commit run --files {{files}}

# Update pre-commit hooks to latest versions
pre-commit-update:
    uv run pre-commit autoupdate

# Run pre-commit without making changes (for CI)
pre-commit-check:
    uv run pre-commit run --all-files --show-diff-on-failure


# Setup development environment (install deps and pre-commit hooks)
setup:
    uv sync --all-extras
    uv run pre-commit install
    @echo "Development environment ready! Pre-commit hooks installed."
