# Installation Guide

Detailed instructions for setting up the Microsoft Agent Framework.

## Prerequisites

### Required

- **Python 3.10+** — Runtime environment
- **Azure OpenAI resource** — With deployed model (gpt-4o recommended)
- **Azure CLI** — For authentication

### Optional

- **Docker** — For containerized deployment
- **Redis** — For session caching (recommended for production)

## Installation Methods

### Method 1: pip install (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install package
pip install -e .
```

### Method 2: pip install with extras

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install with observability extras
pip install -e ".[observability]"

# Install with multi-model support
pip install -e ".[multi-model]"

# Install everything
pip install -e ".[all]"
```

### Method 3: Docker

```bash
# Build image
docker build -t msft-agent:latest -f deployment/Dockerfile .

# Run container
docker run -e AZURE_OPENAI_ENDPOINT=... -e AZURE_OPENAI_DEPLOYMENT=gpt-4o msft-agent:latest
```

## Post-Installation Setup

### 1. Configure Azure Authentication

```bash
# Login to Azure CLI
az login

# Verify login
az account show

# Set subscription (if needed)
az account set --subscription "Your Subscription"
```

### 2. Create Configuration File

```bash
cp config/agent.toml.example config/agent.toml
```

Edit `config/agent.toml`:

```toml
[agent.azure_openai]
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
```

### 3. Verify Installation

```python
# test_installation.py
import asyncio
from src.agent import AIAssistant

async def main():
    try:
        async with AIAssistant() as assistant:
            health = await assistant.health_check()
            print(f"Status: {health.status}")
            print("Installation verified!")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

```bash
python test_installation.py
```

## Development Setup

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This includes:
- `pytest` — Testing framework
- `pytest-asyncio` — Async test support
- `pytest-cov` — Coverage reporting
- `black` — Code formatting
- `ruff` — Linting
- `mypy` — Type checking

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agent.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## IDE Setup

### VS Code

Install recommended extensions:
- Python
- Pylance
- Black Formatter
- Ruff

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

### PyCharm

1. Set interpreter to `.venv/bin/python`
2. Enable Black formatter (Settings > Tools > Black)
3. Enable Ruff linter (Settings > Tools > External Tools)

## Troubleshooting Installation

### Module Not Found

```
ModuleNotFoundError: No module named 'src'
```

**Solution:** Install in editable mode:

```bash
pip install -e .
```

### Azure Authentication Failed

```
DefaultAzureCredential failed to retrieve a token
```

**Solution:**

```bash
az login
az account set --subscription "Your Subscription"
```

### Missing Dependencies

```
ImportError: No module named 'openai'
```

**Solution:** Reinstall the package:

```bash
pip install -e ".[all]"
```

### Python Version Error

```
This package requires Python 3.10+
```

**Solution:** Upgrade Python or use pyenv:

```bash
pyenv install 3.12
pyenv local 3.12
```

## Next Steps

- [Configuration Guide](configuration.md) — Configure your agent
- [Quick Start](quick-start.md) — Run your first agent
- [Architecture](../architecture/index.md) — Understand how it works
