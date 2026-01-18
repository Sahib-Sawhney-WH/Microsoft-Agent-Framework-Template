# Microsoft Agent Framework Template

[![CI](https://github.com/your-org/msft-agent-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/msft-agent-framework/actions/workflows/ci.yml)
[![CD](https://github.com/your-org/msft-agent-framework/actions/workflows/cd.yml/badge.svg)](https://github.com/your-org/msft-agent-framework/actions/workflows/cd.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready AI agent template using the [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview) with dynamic tool loading, MCP support, multi-model providers, and enterprise features.

## Features

- **Dynamic Tool Loading** — Hybrid decorator + JSON tool discovery
- **Multi-Model Support** — Azure OpenAI, OpenAI, and custom providers via registry
- **MCP Integration** — Connect to external MCP servers (stdio, HTTP, WebSocket)
- **Multi-Agent Workflows** — Sequential and graph-based agent pipelines
- **Session Management** — Redis cache + ADLS persistence with auto-summarization
- **Observability** — OpenTelemetry tracing and metrics
- **Security** — Rate limiting, input validation, prompt injection detection
- **Health Checks** — Kubernetes-ready readiness/liveness probes

## Quick Start

### 5-Minute Setup

```bash
# Clone and install
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework
pip install -e .

# Configure
cp config/agent.toml.example config/agent.toml
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Run
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

For detailed setup instructions, see the [Quick Start Guide](docs/getting-started/quick-start.md).

## Deployment Options

| Method | Best For | Guide |
|--------|----------|-------|
| **Local Python** | Development, testing | [Local Development](docs/deployment/local-development.md) |
| **Docker Compose** | Local dev with services | [Docker Guide](docs/deployment/docker.md) |
| **Kubernetes** | Production, scaling | [Kubernetes Guide](docs/deployment/kubernetes.md) |
| **Azure Container Apps** | Serverless Azure | [ACA Guide](docs/deployment/azure-container-apps.md) |

### Docker Compose (Recommended for Development)

```bash
# Start agent with Redis and Jaeger
docker-compose up -d

# View logs
docker-compose logs -f agent

# Access services
# Agent: http://localhost:8080
# Jaeger UI: http://localhost:16686
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/

# Check status
kubectl get pods -n msft-agent
```

## Project Structure

```
msft-agent-framework/
├── config/
│   ├── agent.toml.example     # Configuration template
│   ├── system_prompt.txt      # Agent system prompt
│   └── tools/                 # JSON tool definitions
├── src/
│   ├── agent/                 # Core agent (AIAssistant)
│   ├── config/                # Configuration loader
│   ├── loaders/               # Tool, MCP, workflow loaders
│   ├── memory/                # Session management
│   ├── models/                # Model provider registry
│   ├── observability/         # Tracing and metrics
│   ├── security/              # Security middleware
│   └── tools/                 # Tool decorators
├── deployment/
│   ├── Dockerfile             # Multi-stage Docker build
│   └── kubernetes/            # K8s manifests
├── docs/                      # Documentation
└── tests/                     # Test suite
```

## Configuration

### Environment Variables

```bash
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Optional (for key-based auth)
AZURE_OPENAI_API_KEY=your-key

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

See [Environment Variables Reference](docs/reference/environment-variables.md) for all options.

### agent.toml

```toml
[agent]
name = "my-agent"
default_model = "gpt-4o"

[[agent.models]]
name = "gpt-4o"
provider = "azure_openai"
deployment = "gpt-4o"

[agent.memory.cache]
type = "redis"
host = "localhost"
```

See [Configuration Reference](docs/reference/configuration-reference.md) for all options.

## Adding Tools

```python
from src.tools import ai_function, register_tool, Annotated, Field

@register_tool(tags=["utilities"])
@ai_function
def weather_lookup(
    location: Annotated[str, Field(description="City name")],
    units: str = "fahrenheit",
) -> str:
    """Get current weather for a location."""
    return f"Weather in {location}: Sunny, 72°F"
```

Register in `config/agent.toml`:

```toml
[agent.tools]
tool_modules = ["src.my_tools"]
```

See [Tools Guide](docs/guides/tools.md) for advanced patterns.

## Usage Examples

### Streaming Response

```python
async with AIAssistant() as assistant:
    async for chunk in await assistant.process_question_stream("Tell me a joke"):
        print(chunk.text, end="", flush=True)
```

### Run Workflow

```python
async with AIAssistant() as assistant:
    result = await assistant.run_workflow("content-pipeline", "Write about AI")
    print(result.response)
```

### Session Continuity

```python
async with AIAssistant() as assistant:
    result1 = await assistant.process_question("My name is Alice")
    chat_id = result1.chat_id

    result2 = await assistant.process_question("What's my name?", chat_id=chat_id)
    # Response: "Your name is Alice"
```

### Health Check

```python
async with AIAssistant() as assistant:
    health = await assistant.health_check()
    print(f"Status: {health.status}")  # healthy, degraded, unhealthy
```

## Documentation

### Getting Started

| Guide | Description |
|-------|-------------|
| [Quick Start](docs/getting-started/quick-start.md) | 5-minute setup |
| [Installation](docs/getting-started/installation.md) | Detailed installation |
| [Configuration](docs/getting-started/configuration.md) | Configuration guide |

### Guides

| Guide | Description |
|-------|-------------|
| [Architecture](docs/architecture/index.md) | System design and components |
| [Tools](docs/guides/tools.md) | Creating and registering tools |
| [Memory](docs/guides/memory.md) | Session and conversation management |
| [MCP Integration](docs/guides/mcp-integration.md) | External tool servers |
| [Workflows](docs/guides/workflows.md) | Multi-agent pipelines |
| [Security](docs/guides/security.md) | Security features |
| [Observability](docs/guides/observability.md) | Tracing and metrics |

### Deployment

| Guide | Description |
|-------|-------------|
| [Local Development](docs/deployment/local-development.md) | Development setup |
| [Docker](docs/deployment/docker.md) | Docker deployment |
| [Kubernetes](docs/deployment/kubernetes.md) | K8s deployment |
| [Azure Container Apps](docs/deployment/azure-container-apps.md) | Serverless deployment |
| [Azure Setup](docs/deployment/azure-setup.md) | Azure resource configuration |
| [Production Checklist](docs/deployment/production-checklist.md) | Go-live checklist |

### Operations

| Guide | Description |
|-------|-------------|
| [Monitoring](docs/operations/monitoring.md) | Dashboards and alerts |
| [Troubleshooting](docs/operations/troubleshooting.md) | Common issues |
| [Scaling](docs/operations/scaling.md) | Performance tuning |

### Reference

| Document | Description |
|----------|-------------|
| [Configuration Reference](docs/reference/configuration-reference.md) | All config options |
| [Environment Variables](docs/reference/environment-variables.md) | Env var reference |

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Contributing

We welcome contributions! Please see [Contributing Guide](docs/contributing/index.md) for:

- Development setup
- Code standards
- Pull request process
- Testing requirements

## Requirements

- Python 3.10+
- Azure OpenAI resource with deployed model
- Azure identity configured (DefaultAzureCredential recommended)
- Redis (optional, for session caching)
- Azure Storage (optional, for persistence)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- [Documentation](docs/index.md)
- [Troubleshooting Guide](docs/operations/troubleshooting.md)
- [GitHub Issues](https://github.com/your-org/msft-agent-framework/issues)
