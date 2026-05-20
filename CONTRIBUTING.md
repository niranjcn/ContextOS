# Contributing to ContextOS

Thank you for your interest in contributing to ContextOS! This document provides
guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository
2. Install dev dependencies: `make install-dev`
3. Copy `.env.example` to `.env` and configure
4. Run tests: `make test`

## Code Standards

- **Type hints** on every function signature
- **Docstrings** on every class and public method (Google style)
- **Logging** via `logging.getLogger(__name__)` — no `print()` statements
- **Error handling** — never bare `except:`, always catch specific exceptions
- **No hardcoded strings** — all config comes from `settings`
- **Dataclasses or Pydantic models** for all structured data

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for any new functionality
3. Ensure all tests pass: `make test`
4. Ensure code passes linting: `make lint`
5. Update documentation if needed
6. Submit a PR with a clear description of changes

## Dependency Direction

The import dependency direction must be strictly maintained:

```
config → storage → ingestion → inference → api
```

No circular imports are allowed.

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Python version and OS
- Relevant log output
