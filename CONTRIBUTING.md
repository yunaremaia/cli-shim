# Contributing to cli-shim

Thank you for your interest in contributing to **cli-shim**! We welcome contributions, whether you're adding support for new CLI tools, fixing bugs, or improving documentation.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Adding a New CLI to the Registry](#adding-a-new-cli-to-the-registry)
- [Testing](#testing)
- [Code Style and Linting](#code-style-and-linting)
- [Pull Request Guidelines](#pull-request-guidelines)

---

## Development Setup

### Prerequisites

- **Python 3.8+**
- **Git**
- A virtual environment tool (`venv`, `virtualenv`, or `conda`)

### Step-by-Step Setup

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/<your-username>/cli-shim.git
   cd cli-shim
   ```

2. **Create and activate a virtual environment:**

   ```bash
   # On macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install in editable mode with development dependencies:**

   ```bash
   pip install -e .
   pip install pytest ruff
   ```

4. **Verify the installation:**

   ```bash
   shim --version
   pytest
   ```

---

## Architecture Overview

`cli-shim` serves as a universal adapter between legacy CLI utilities and AI agents (such as Claude Code, Cursor, Codex, OpenClaw, and Hermes).

```
                ┌───────────────────────────┐
                │        Input CLI          │
                └─────────────┬─────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Agent Detection  │ (CLAUDECODE, AI_AGENT, etc.)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Registry Lookup  │ (JSON_MAP, NON_INTERACTIVE_MAP)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Flag Injection   │ (--json, --yes, --quiet)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Execution Guard   │ (TERM=dumb, Subprocess Runner)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Output Normalizer │ (ANSI Stripping, Stream Split)
                    └─────────┬─────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
      ┌─────▼──────┐                      ┌─────▼──────┐
      │   stdout   │                      │   stderr   │
      │ Clean Data │                      │ Decor/Err  │
      └────────────┘                      └────────────┘
```

The core pipeline operates in five stages in `cli_shim/__init__.py`:

1. **Agent Environment Detection (`is_agent_mode`):**  
   Checks environment variables (`CLAUDECODE`, `AI_AGENT`, `OPENCLAW_AGENT`, `CODEX_SESSION`, `HERMES_CRON`). When detected, agent-specific sanitization is enabled.
2. **Registry Lookup & Flag Injection (`make_non_interactive`, `discover_json_flag`, `inject_json_flag`):**  
   Maps base commands to their respective non-interactive and JSON flags, inserting them after the subcommand to avoid breaking tool syntax.
3. **Execution Isolation (`run_shim`):**  
   Executes the wrapped process with `TERM=dumb` to discourage tools from outputting curses-based interactive interfaces or animations.
4. **ANSI Stripping & Stream Splitting (`strip_ansi`, `split_output`):**  
   Removes ANSI escape codes from stdout in agent mode so models receive machine-readable data, while routing decorative banners and errors to stderr.
5. **Dynamic Manifest Discovery (`discover_manifest`):**  
   Parses `--help` text for unknown tools to dynamically discover subcommands and flag capabilities.

---

## Adding a New CLI to the Registry

Adding support for a new CLI is simple and involves registering its flags in `cli_shim/__init__.py`.

### Step 1: Identify the CLI's Flags

Determine how the CLI handles:
- **Non-interactive mode:** (e.g., `--yes`, `-y`, `--quiet`, `--no-input`, or `--batch`)
- **JSON output:** (e.g., `--json`, `-o=json`, `--output=json`, `--format=json`, or `-json`)

### Step 2: Register in `cli_shim/__init__.py`

1. Open `cli_shim/__init__.py`.
2. Locate `NON_INTERACTIVE_MAP` in `make_non_interactive()` and add your CLI:

   ```python
   NON_INTERACTIVE_MAP = {
       ...
       "mytool": ["--yes"],  # or ["--quiet"], ["-y"], etc.
   }
   ```

3. Locate `JSON_MAP` in `discover_json_flag()` and add your CLI:

   ```python
   JSON_MAP = {
       ...
       "mytool": "--json",   # or "-o=json", "--output=json", etc.
   }
   ```

### Step 3: Add Unit Tests

Add test cases in `tests/test_cli_shim.py`:

```python
class TestMakeNonInteractive:
    ...
    def test_mytool(self):
        assert make_non_interactive(["mytool", "deploy"]) == ["mytool", "--yes", "deploy"]

class TestDiscoverJsonFlag:
    ...
    def test_mytool(self):
        assert discover_json_flag(["mytool", "status"]) == "--json"
```

---

## Testing

We use [pytest](https://docs.pytest.org/) for automated testing.

### Running Tests

Run the full test suite:

```bash
pytest
```

Run with verbose output and coverage:

```bash
pytest -v
```

Run a specific test class or method:

```bash
pytest tests/test_cli_shim.py -k "TestMakeNonInteractive"
```

Ensure all tests pass before submitting your pull request.

---

## Code Style and Linting

We maintain high code quality with [Ruff](https://docs.astral.sh/ruff/):

- **Check code for lint issues:**

  ```bash
  ruff check .
  ```

- **Automatically fix lint issues:**

  ```bash
  ruff check --fix .
  ```

- **Format code:**

  ```bash
  ruff format .
  ```

### Style Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) naming and formatting standards.
- Use explicit type annotations where possible.
- Avoid introducing heavy third-party runtime dependencies; keep `cli-shim` lightweight and fast.

---

## Pull Request Guidelines

1. **Create a feature branch:**
   ```bash
   git checkout -b feat/add-mytool-support
   ```
2. **Keep PRs focused:** Submit one pull request per CLI tool or feature.
3. **Write meaningful commit messages:** Use conventional prefixes such as `feat:`, `fix:`, `docs:`, or `test:`.
4. **Reference related issues:** In your PR description, link the issue (e.g., `Fixes #31`).
5. **Verify checks:** Ensure all unit tests and lint checks pass cleanly.
