# Local Development Setup

This guide covers setting up a local development environment for the Microsoft Agent Framework.

## Prerequisites

- **Python 3.10+** — Required runtime
- **Azure CLI** — For Azure authentication (`az login`)
- **Azure OpenAI resource** — With a deployed model (gpt-4o recommended)
- **Docker** (optional) — For running Redis and Jaeger locally

## Quick Start

### Option 1: Python Only (Simplest)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure
cp config/agent.toml.example config/agent.toml
# Edit config/agent.toml with your Azure OpenAI credentials

# 5. Login to Azure (for DefaultAzureCredential)
az login

# 6. Run the agent
python -c "
import asyncio
from src.agent import AIAssistant

async def main():
    async with AIAssistant() as assistant:
        result = await assistant.process_question('Hello!')
        print(result.response)

asyncio.run(main())
"
```

### Option 2: Docker Compose (Full Stack)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your Azure OpenAI credentials
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=gpt-4o

# 4. Start all services
docker-compose up -d

# 5. Verify services are running
docker-compose ps

# 6. View logs
docker-compose logs -f agent
```

**Services available:**
- Agent API: http://localhost:8080
- Jaeger UI: http://localhost:16686
- Redis: localhost:6379

## Configuration

### TOML Configuration

The primary configuration file is `config/agent.toml`:

```toml
[agent]
system_prompt = "config/system_prompt.txt"
log_level = "DEBUG"  # More verbose for development

[agent.azure_openai]
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
api_version = "2024-10-01-preview"

# Local Redis (Docker Compose)
[agent.memory.cache]
enabled = true
host = "localhost"
port = 6379
ssl = false
ttl = 3600

# Disable ADLS for local development
[agent.memory.persistence]
enabled = false
```

### Environment Variables

You can override TOML settings with environment variables:

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
export LOG_LEVEL="DEBUG"
```

See [Environment Variables Reference](../reference/environment-variables.md) for all options.

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only unit tests (skip integration)
pytest tests/ -v -m "not integration"
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Interactive Development

```python
# Start Python REPL with the agent loaded
python -i -c "
import asyncio
from src.agent import AIAssistant

assistant = None

async def init():
    global assistant
    assistant = AIAssistant()
    await assistant.initialize()
    return assistant

async def ask(q):
    result = await assistant.process_question(q)
    print(result.response)
    return result

print('Run: asyncio.run(init())')
print('Then: asyncio.run(ask(\"Your question\"))')
"
```

### Hot Reload (Development Server)

For rapid development, you can use `watchfiles` for auto-reload:

```bash
pip install watchfiles

watchfiles "python -m src.agent.assistant" src/
```

## Local Services

### Redis (Session Cache)

**Option A: Docker**

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Option B: Docker Compose** (included in docker-compose.yml)

```bash
docker-compose up -d redis
```

**Verify Redis:**

```bash
docker exec -it redis redis-cli ping
# Output: PONG
```

### Jaeger (Tracing)

**Start Jaeger:**

```bash
docker-compose up -d jaeger
```

**Access Jaeger UI:** http://localhost:16686

**Configure tracing in agent.toml:**

```toml
[agent.observability]
tracing_enabled = true
tracing_exporter = "jaeger"
```

## Debugging

### Enable Debug Logging

```toml
# config/agent.toml
[agent]
log_level = "DEBUG"
```

Or via environment:

```bash
export LOG_LEVEL=DEBUG
```

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Agent",
      "type": "python",
      "request": "launch",
      "module": "src.agent.assistant",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "-s"],
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

### PyCharm Configuration

1. Create a new Run Configuration
2. Set Script path to `src/agent/assistant.py`
3. Set Working directory to project root
4. Add environment variable `LOG_LEVEL=DEBUG`

## Common Issues

### Azure Authentication Errors

```
Error: DefaultAzureCredential failed to retrieve a token
```

**Solution:**

```bash
# Login to Azure CLI
az login

# Verify logged in account
az account show

# Set specific subscription if needed
az account set --subscription "Your Subscription Name"
```

### Redis Connection Refused

```
Error: Connection refused (localhost:6379)
```

**Solution:**

```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis if not running
docker-compose up -d redis
```

### Module Not Found Errors

```
Error: ModuleNotFoundError: No module named 'src'
```

**Solution:**

```bash
# Install in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Port Already in Use

```
Error: Port 8080 already in use
```

**Solution:**

```bash
# Find process using port
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill the process or use a different port
export PORT=8081
```

## Next Steps

- [Docker Deployment](docker.md) — Build and run containers
- [Configuration Reference](../reference/configuration-reference.md) — All configuration options
- [Tools Guide](../guides/tools.md) — Create custom tools
- [Testing Guide](../contributing/development-setup.md) — Testing best practices
