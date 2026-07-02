# Contributing to ComputeForge

We love contributions! ComputeForge is an open-source project and we welcome
contributions of all kinds: bug fixes, features, documentation, and ideas.

## Getting Started

1. Fork the repository
2. Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
3. Install development dependencies: `pip install -e ".[dev]"`
4. Install Playwright browsers: `playwright install chromium`
5. Create a branch: `git checkout -b feature/my-feature`

## Development Workflow

```bash
# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/

# Format
ruff format src/
```

## Code Style

- Python 3.12+ with type hints
- Follow existing patterns in the codebase
- Use `ruff` for linting and formatting
- All public APIs should have docstrings
- Async-first design for I/O operations

## Pull Request Process

1. Ensure all tests pass
2. Add tests for new functionality
3. Update documentation if needed
4. Keep PRs focused on a single change
5. Reference any related issues

## Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Questions?

Open an issue or discussion on GitHub.
