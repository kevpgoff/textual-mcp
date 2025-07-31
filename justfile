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

# Run type checking with mypy
typecheck:
    {{python}} -m mypy src/textual_mcp/

# Run mypy on specific file or directory
typecheck-file path:
    {{python}} -m mypy {{path}}

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