# AGENT.md<!-- omit from toc -->

**Contents**

- [Project: brAIngentX](#project-braingentx)
  - [1. Stack \& Environment](#1-stack--environment)
  - [2. Coding \& Testing Standards](#2-coding--testing-standards)
  - [3. Agent Usage \& Safety](#3-agent-usage--safety)
  - [4. Repository Structure (Key Paths)](#4-repository-structure-key-paths)
  - [5. Commands for Agents](#5-commands-for-agents)
  - [6. License](#6-license)
  - [7. References](#7-references)


## Project: brAIngentX

**Purpose:**
A skills management toolkit for agentic AI projects, enabling autonomous scripts to manage, share, and activate skills across multiple repositories. Designed for robust, type-safe, and maintainable Python codebases.

### 1. Stack & Environment
- **Python Version:** 3.10+
- **Dependency Management:** [uv](https://github.com/astral-sh/uv) (`uv run`, `uv add`, `uv sync`)
- **Linting/Formatting:** [ruff](https://docs.astral.sh/ruff/) (`ruff check --fix`, `ruff format`)
- **Type Checking:** [basedpyright](https://github.com/microsoft/pyright)
- **Virtual Environment:** `.venv` (created/managed by uv)
- **Data Modeling:** Prefer [Pydantic v2](https://docs.pydantic.dev/) if present

### 2. Coding & Testing Standards
- **Code Style:**
  - Strict PEP 8 compliance (see `.github/instructions/python-style.instructions.md`)
  - Type hints required for all function signatures
  - Strict type-checking as defined in `pyproject.toml`
- **Testing:**
  - Use `pytest` (see `.github/instructions/python-tests.instructions.md`)
  - Place tests in `tests/` as `test_*.py`
  - Use fixtures, parameterization, and Arrange-Act-Assert comments
- **Security:**
  - Follow secure development practices (see `.github/instructions/secure-development.instructions.md`)
  - Never hardcode secrets or credentials

### 3. Agent Usage & Safety
- **Primary Agent Tasks:**
  - Logic implementation, type refactoring, ruff-based linting/fixing
- **Restricted Agent Tasks:**
  - Bypassing type checks, manual pip installs, production deployment, secret rotation
- **Required Pre-Reads for Agents:**
  - `pyproject.toml`, `.python-version`, `.github/instructions/*`, this `AGENT.md`

### 4. Repository Structure (Key Paths)
- `bin/braingentx.py` — Main CLI for skill management
- `tests/` — Pytest-based test suite
- `.agents/skills/` — Skill definitions and agent instructions
- `.github/instructions/` — Style, test, and security standards

### 5. Commands for Agents
- **Install dependencies:**
  - `uv sync`
- **Add a package:**
  - `uv add <package>`
- **Run tests:**
  - `uv run pytest`
- **Lint & format:**
  - `ruff check --fix .`
  - `ruff format .`
- **Type check:**
  - `basedpyright`

### 6. License
- Apache 2.0 (see LICENSE)

### 7. References
- [python-style.instructions.md](.github/instructions/python-style.instructions.md)
- [python-tests.instructions.md](.github/instructions/python-tests.instructions.md)
- [secure-development.instructions.md](.github/instructions/secure-development.instructions.md)

*This file is machine-optimized for AI agent onboarding and safe, maintainable Python development.*
