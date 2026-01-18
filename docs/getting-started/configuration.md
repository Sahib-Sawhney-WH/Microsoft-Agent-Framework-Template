# Configuration Guide

Learn how to configure the Microsoft Agent Framework for your needs.

## Configuration Methods

The framework supports multiple configuration methods with the following precedence:

1. **Environment variables** (highest priority)
2. **TOML configuration file** (`config/agent.toml`)
3. **Default values** (lowest priority)

## Quick Configuration

### Minimal Configuration

Create `config/agent.toml`:

```toml
[agent.azure_openai]
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
```

Or use environment variables:

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
```

## TOML Configuration Reference

### Agent Settings

```toml
[agent]
# Path to system prompt file
system_prompt = "config/system_prompt.txt"

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level = "INFO"

# Default model to use
default_model = "azure_openai"
```

### Azure OpenAI

```toml
[agent.azure_openai]
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
api_version = "2024-10-01-preview"
```

### Multi-Model Providers

```toml
# Azure OpenAI (default)
[[agent.models]]
name = "azure_openai"
provider = "azure_openai"
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
api_version = "2024-10-01-preview"

# OpenAI Direct
[[agent.models]]
name = "openai"
provider = "openai"
model = "gpt-4-turbo"
# Uses OPENAI_API_KEY env var

# Anthropic Claude
[[agent.models]]
name = "claude"
provider = "anthropic"
model = "claude-3-opus-20240229"
# Uses ANTHROPIC_API_KEY env var
```

### Tool Configuration

```toml
[agent.tools]
# Directory for JSON tool definitions
config_dir = "config/tools"

# Python modules to load tools from
tool_modules = ["src.example_tool.tools", "src.my_tools"]

# Enable/disable JSON tools
enable_json_tools = true

# Enable/disable decorator tools
enable_decorator_tools = true
```

### MCP Servers

```toml
# Stdio MCP server (subprocess)
[[agent.mcp]]
name = "calculator"
type = "stdio"
enabled = true
command = "uvx"
args = ["mcp-server-calculator"]

# HTTP/SSE MCP server
[[agent.mcp]]
name = "api-service"
type = "http"
enabled = true
url = "https://api.example.com/mcp"
headers = { Authorization = "Bearer ${API_TOKEN}" }

# WebSocket MCP server
[[agent.mcp]]
name = "realtime"
type = "websocket"
enabled = true
url = "wss://api.example.com/mcp"
```

### Memory Configuration

```toml
[agent.memory]
enabled = true

# Redis Cache
[agent.memory.cache]
enabled = true
host = "your-redis.redis.cache.windows.net"
port = 6380
ssl = true
ttl = 3600
prefix = "chat:"
database = 0

# Blob Persistence
[agent.memory.persistence]
enabled = true
account_name = "yourstorageaccount"
container = "chat-history"
folder = "threads"
schedule = "ttl+300"

# Context Summarization
[agent.memory.summarization]
enabled = true
max_tokens = 8000
summary_target_tokens = 2000
recent_messages_to_keep = 5
```

### Security Configuration

```toml
[agent.security.rate_limit]
enabled = true
requests_per_minute = 60
requests_per_hour = 1000
tokens_per_minute = 100000
max_concurrent_requests = 10
per_user = true

[agent.security.validation]
max_question_length = 32000
max_tool_param_length = 10000
block_prompt_injection = true
block_pii = false
redact_pii = true
blocked_patterns = ["confidential", "internal only"]
```

### Observability Configuration

```toml
[agent.observability]
# Tracing
tracing_enabled = true
tracing_exporter = "otlp"  # console, otlp, azure, jaeger

# Metrics
metrics_enabled = true
metrics_exporter = "prometheus"  # console, prometheus, azure, otlp

# Service identification
service_name = "ai-assistant"
service_version = "1.0.0"
environment = "production"
```

### Workflow Configuration

```toml
[[agent.workflows]]
name = "content-pipeline"
type = "sequential"
enabled = true

[[agent.workflows.agents]]
name = "Researcher"
instructions = "Research the topic and provide key facts."
# model = "openai"  # Optional: use specific model

[[agent.workflows.agents]]
name = "Writer"
instructions = "Write engaging content based on the research."

[[agent.workflows.agents]]
name = "Reviewer"
instructions = "Review and polish the final content."
```

## Environment Variables

Environment variables override TOML configuration.

### Azure OpenAI

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | API version |

### Azure Authentication

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |

### Redis

| Variable | Description |
|----------|-------------|
| `REDIS_HOST` | Redis hostname |
| `REDIS_PORT` | Redis port |
| `REDIS_SSL` | Use SSL (true/false) |
| `REDIS_TTL` | Cache TTL in seconds |

### Storage

| Variable | Description |
|----------|-------------|
| `STORAGE_ACCOUNT_NAME` | Azure Storage account |
| `STORAGE_CONTAINER` | Blob container name |

### Observability

| Variable | Description |
|----------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor connection |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | Service name for tracing |

### Application

| Variable | Description |
|----------|-------------|
| `LOG_LEVEL` | Logging level |
| `ENVIRONMENT` | Environment name |

## Customizing System Prompt

Edit `config/system_prompt.txt` to customize your agent's behavior:

```text
You are a helpful AI assistant for [Your Company].

Your responsibilities:
- Answer questions about [topic]
- Help users with [tasks]

Guidelines:
- Be concise and professional
- Ask for clarification when needed
- Cite sources when providing information
```

## Configuration Best Practices

### Development

```toml
[agent]
log_level = "DEBUG"

[agent.memory.cache]
enabled = false  # Use in-memory for development

[agent.observability]
tracing_enabled = true
tracing_exporter = "console"
```

### Production

```toml
[agent]
log_level = "INFO"

[agent.memory.cache]
enabled = true
host = "your-redis.redis.cache.windows.net"

[agent.security.rate_limit]
enabled = true
per_user = true

[agent.observability]
tracing_enabled = true
tracing_exporter = "azure"
```

## Validating Configuration

```python
from src.config import load_config

# Load and validate configuration
config = load_config()

# Print configuration
print(f"Endpoint: {config.azure_openai.endpoint}")
print(f"Deployment: {config.azure_openai.deployment}")
print(f"Cache enabled: {config.memory.cache.enabled}")
```

## Next Steps

- [Architecture Overview](../architecture/index.md) — Understand the system
- [Tools Guide](../guides/tools.md) — Create custom tools
- [Deployment Guide](../deployment/index.md) — Deploy to production
