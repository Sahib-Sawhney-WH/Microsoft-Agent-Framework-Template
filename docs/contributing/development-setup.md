# Development Setup

Complete guide for setting up a local development environment.

## Prerequisites

### Required

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.10+ | `python --version` |
| pip | Latest | `pip --version` |
| Git | Any | `git --version` |

### Optional (Recommended)

| Tool | Purpose | Install |
|------|---------|---------|
| Docker | Local services | [Install Docker](https://docs.docker.com/get-docker/) |
| Azure CLI | Azure development | `pip install azure-cli` |
| uv | Fast Python packages | `pip install uv` |

## Quick Setup

```bash
# Clone repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Copy configuration
cp config/agent.toml.example config/agent.toml
cp .env.example .env

# Install pre-commit hooks
pre-commit install
```

## Detailed Setup

### 1. Python Environment

#### Option A: venv (Standard)

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Verify
which python  # Should point to .venv
```

#### Option B: pyenv + venv

```bash
# Install Python version
pyenv install 3.12.0
pyenv local 3.12.0

# Create venv
python -m venv .venv
source .venv/bin/activate
```

#### Option C: uv (Fast)

```bash
# Install uv
pip install uv

# Create and activate
uv venv .venv
source .venv/bin/activate

# Install with uv (faster)
uv pip install -e ".[dev]"
```

### 2. Install Dependencies

```bash
# Development install (editable)
pip install -e ".[dev]"

# This installs:
# - Core dependencies
# - Dev tools (pytest, ruff, mypy)
# - Pre-commit hooks
```

### 3. Configuration

#### Environment Variables

Create `.env` from template:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Azure OpenAI (required for full testing)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here  # Or use Azure CLI auth

# Local Redis (for integration tests)
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Configuration File

```bash
cp config/agent.toml.example config/agent.toml
```

Minimal development config:

```toml
[agent]
name = "dev-agent"
log_level = "DEBUG"
default_model = "gpt-4o"

[[agent.models]]
name = "gpt-4o"
provider = "azure_openai"
deployment = "gpt-4o"
api_version = "2024-08-01-preview"

[agent.memory.in_memory]
enabled = true

[agent.memory.cache]
type = "redis"
host = "localhost"
port = 6379
```

### 4. Local Services

Start Redis and Jaeger for development:

```bash
docker-compose up -d redis jaeger
```

Or run Redis standalone:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Verify services:

```bash
# Redis
redis-cli ping  # Should return PONG

# Jaeger (open in browser)
# http://localhost:16686
```

### 5. Pre-commit Hooks

Install hooks for automatic code quality:

```bash
pre-commit install
```

This runs before each commit:
- Ruff (linting + formatting)
- MyPy (type checking)
- Trailing whitespace removal
- YAML validation

Run manually:

```bash
pre-commit run --all-files
```

## IDE Setup

### VS Code

Recommended extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-azuretools.vscode-docker"
  ]
}
```

Settings:

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.lint.args": ["--config=pyproject.toml"]
}
```

### PyCharm

1. Open project folder
2. Configure interpreter: `.venv/bin/python`
3. Enable Ruff plugin
4. Set pytest as test runner

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Specific Tests

```bash
# Single file
pytest tests/test_agent.py -v

# Single test
pytest tests/test_agent.py::test_process_question -v

# By marker
pytest -m "not slow" -v
```

### With Coverage

```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
# Open htmlcov/index.html in browser
```

### Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw tests/ -- -v
```

## Code Quality

### Linting

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Checking

```bash
# Run mypy
mypy src/

# Strict mode
mypy src/ --strict
```

### All Checks

```bash
# Run all pre-commit checks
pre-commit run --all-files
```

## Development Workflow

### 1. Create Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit code, add tests, update docs.

### 3. Test Locally

```bash
# Quick test
pytest tests/ -v -x  # Stop on first failure

# Full test
pytest tests/ -v --cov=src
```

### 4. Check Quality

```bash
ruff check src/ tests/
mypy src/
```

### 5. Commit

```bash
git add .
git commit -m "feat: add new feature"
```

Pre-commit hooks run automatically.

### 6. Push and PR

```bash
git push origin feature/my-feature
# Create PR on GitHub
```

## Debugging

### VS Code Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Agent",
      "type": "debugpy",
      "request": "launch",
      "module": "src.main",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Debug Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "-s"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Logging

Enable debug logging:

```toml
# config/agent.toml
[agent]
log_level = "DEBUG"
```

Or via environment:

```bash
export LOG_LEVEL=DEBUG
```

### Tracing

View traces in Jaeger:

1. Start Jaeger: `docker-compose up -d jaeger`
2. Run your code
3. Open http://localhost:16686
4. Select service and find traces

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify PYTHONPATH
python -c "import src; print(src.__file__)"
```

### Redis Connection Failed

```bash
# Check Redis is running
docker ps | grep redis

# Start if needed
docker-compose up -d redis
```

### Azure Auth Issues

```bash
# Login to Azure CLI
az login

# Set subscription
az account set --subscription "Your Subscription"

# Verify
az account show
```

### Pre-commit Failures

```bash
# Update hooks
pre-commit autoupdate

# Run manually to see errors
pre-commit run --all-files --verbose
```

## Common Commands Reference

| Task | Command |
|------|---------|
| Install deps | `pip install -e ".[dev]"` |
| Run tests | `pytest tests/ -v` |
| Run linter | `ruff check src/` |
| Format code | `ruff format src/` |
| Type check | `mypy src/` |
| Start services | `docker-compose up -d` |
| View logs | `docker-compose logs -f` |
| Stop services | `docker-compose down` |

## Related Documentation

- [Contributing Guide](index.md) — Contribution process
- [Local Development](../deployment/local-development.md) — Running the agent
- [Configuration](../getting-started/configuration.md) — Config options
