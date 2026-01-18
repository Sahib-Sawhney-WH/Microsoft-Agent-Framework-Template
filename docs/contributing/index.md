# Contributing Guide

Thank you for your interest in contributing to the Microsoft Agent Framework Template!

## Quick Links

| Guide | Description |
|-------|-------------|
| [Development Setup](development-setup.md) | Set up your development environment |

## How to Contribute

### Reporting Issues

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Include reproduction steps** for bugs
4. **Provide environment details** (Python version, OS, etc.)

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Environment details
- Relevant logs or error messages

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternatives considered
- Willingness to implement

## Development Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/msft-agent-framework.git
cd msft-agent-framework
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 4. Make Changes

- Follow code standards (below)
- Add tests for new functionality
- Update documentation if needed

### 5. Test Your Changes

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run linting
ruff check src/
ruff format --check src/

# Run type checking
mypy src/
```

### 6. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add support for custom model providers"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code refactoring
- `test:` — Test additions/changes
- `chore:` — Build/tooling changes

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Standards

### Python Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check linting
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Format code
ruff format src/
```

### Type Hints

All code must include type hints:

```python
# Good
def process_message(message: str, max_tokens: int = 100) -> str:
    ...

# Bad
def process_message(message, max_tokens=100):
    ...
```

Use `mypy` for type checking:

```bash
mypy src/
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Calculate token count for text.

    Args:
        text: The input text to tokenize.
        model: The model to use for tokenization.

    Returns:
        The number of tokens in the text.

    Raises:
        ValueError: If text is empty.

    Example:
        >>> calculate_tokens("Hello world")
        2
    """
    ...
```

### Import Order

```python
# Standard library
import asyncio
import json
from pathlib import Path

# Third-party
import aiohttp
from pydantic import BaseModel

# Local
from src.config import Config
from src.tools import register_tool
```

Ruff handles import sorting automatically.

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_config.py
│   ├── test_tools.py
│   └── test_memory.py
├── integration/             # Integration tests
│   ├── test_agent.py
│   └── test_mcp.py
└── conftest.py              # Shared fixtures
```

### Writing Tests

```python
import pytest
from src.tools import register_tool

class TestToolRegistration:
    """Tests for tool registration."""

    def test_register_basic_tool(self):
        """Test registering a simple tool."""
        @register_tool()
        def my_tool(x: int) -> int:
            return x * 2

        assert my_tool(5) == 10

    def test_register_with_metadata(self):
        """Test registering with custom metadata."""
        @register_tool(name="custom_name", tags=["math"])
        def add(a: int, b: int) -> int:
            return a + b

        # Verify registration
        ...

    @pytest.mark.asyncio
    async def test_async_tool(self):
        """Test async tool execution."""
        @register_tool()
        async def async_tool() -> str:
            return "result"

        result = await async_tool()
        assert result == "result"
```

### Fixtures

Use fixtures for common setup:

```python
# conftest.py
import pytest
from src.config import load_config

@pytest.fixture
def config():
    """Load test configuration."""
    return load_config("tests/fixtures/test_config.toml")

@pytest.fixture
async def assistant(config):
    """Create test assistant."""
    from src.agent import AIAssistant
    async with AIAssistant(config) as assistant:
        yield assistant
```

### Marks

```python
@pytest.mark.slow
def test_large_dataset():
    """Test that takes a long time."""
    ...

@pytest.mark.integration
async def test_azure_connection():
    """Test that requires Azure connection."""
    ...
```

Run specific marks:

```bash
pytest -m "not slow"
pytest -m integration
```

## Documentation

### Updating Docs

- Documentation lives in `docs/`
- Use Markdown with GitHub-flavored extensions
- Include code examples that work
- Add cross-references to related docs

### Structure

```
docs/
├── index.md                 # Landing page
├── getting-started/         # Onboarding
├── guides/                  # How-to guides
├── deployment/              # Deployment docs
├── operations/              # Operations docs
├── reference/               # Technical reference
└── contributing/            # This section
```

### Code Examples

Always test code examples:

```python
# Good - tested example
from src.tools import ai_function

@ai_function
def greet(name: str) -> str:
    """Greet a user."""
    return f"Hello, {name}!"

result = greet("World")
assert result == "Hello, World!"
```

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest tests/`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Types check (`mypy src/`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated
```

### Review Process

1. CI checks must pass
2. At least one approval required
3. Address review feedback
4. Squash and merge

## Questions?

- Check existing [documentation](../index.md)
- Search [issues](https://github.com/your-org/msft-agent-framework/issues)
- Open a discussion for questions

## Related Documentation

- [Development Setup](development-setup.md) — Environment setup
- [Architecture](../architecture/index.md) — System design
- [Testing](../guides/tools.md#testing) — Testing tools
