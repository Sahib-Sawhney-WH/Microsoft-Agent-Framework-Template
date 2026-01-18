# Configuration Reference

Complete reference for all configuration options in `config/agent.toml`.

## Agent Configuration

### Basic Settings

```toml
[agent]
name = "msft-agent"                    # Agent name (alphanumeric, hyphens)
version = "1.0.0"                      # Semantic version
log_level = "INFO"                     # DEBUG, INFO, WARNING, ERROR
default_model = "gpt-4o"               # Default model for requests
max_tokens = 4096                      # Max output tokens
temperature = 0.7                      # Response temperature (0-2)
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | `"msft-agent"` | Agent identifier |
| `version` | string | `"1.0.0"` | Agent version |
| `log_level` | string | `"INFO"` | Logging level |
| `default_model` | string | required | Default LLM model |
| `max_tokens` | int | `4096` | Maximum output tokens |
| `temperature` | float | `0.7` | Response randomness |

### System Prompt

```toml
[agent]
system_prompt = """
You are a helpful AI assistant.
- Be concise and accurate
- Use tools when needed
- Cite sources when available
"""
```

## Model Configuration

### Azure OpenAI Models

```toml
[[agent.models]]
name = "gpt-4o"                        # Model reference name
provider = "azure_openai"              # Provider type
endpoint = ""                          # Uses AZURE_OPENAI_ENDPOINT env var
deployment = "gpt-4o"                  # Azure deployment name
api_version = "2024-08-01-preview"     # API version

[[agent.models]]
name = "gpt-4o-mini"
provider = "azure_openai"
deployment = "gpt-4o-mini"
api_version = "2024-08-01-preview"
```

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | Yes | Unique model reference |
| `provider` | string | Yes | `azure_openai` |
| `endpoint` | string | No | Overrides env var |
| `deployment` | string | Yes | Azure deployment name |
| `api_version` | string | Yes | Azure API version |

### Model Selection

```python
# Use default model
result = await assistant.process_question("Hello")

# Use specific model
result = await assistant.process_question("Hello", model="gpt-4o-mini")
```

## Memory Configuration

### In-Memory Store

```toml
[agent.memory.in_memory]
enabled = true                         # Enable in-memory cache
max_sessions = 1000                    # Max cached sessions
ttl = 3600                             # TTL in seconds
```

### Redis Cache

```toml
[agent.memory.cache]
type = "redis"                         # Cache type
host = "localhost"                     # Redis host
port = 6379                            # Redis port
ssl = false                            # Enable SSL/TLS
password = ""                          # Auth password (use env var)
db = 0                                 # Redis database number
key_prefix = "msft-agent:"             # Key prefix
ttl = 86400                            # TTL in seconds (24 hours)
max_connections = 50                   # Connection pool size
```

#### Azure Cache for Redis (AAD Auth)

```toml
[agent.memory.cache]
type = "redis"
host = "your-redis.redis.cache.windows.net"
port = 6380
ssl = true
use_azure_auth = true                  # Use DefaultAzureCredential
```

### ADLS Persistence

```toml
[agent.memory.persistence]
enabled = true                         # Enable persistence
type = "azure_blob"                    # Storage type
account_name = ""                      # Uses AZURE_STORAGE_ACCOUNT
container_name = "chat-history"        # Blob container
path_prefix = "threads/"               # Path prefix for blobs

# Sync settings
sync_interval = 300                    # Sync every 5 minutes
sync_on_close = true                   # Sync when session closes
```

### Summarization

```toml
[agent.memory.summarization]
enabled = true                         # Enable auto-summarization
max_tokens = 8000                      # Threshold for summarization
summary_model = "gpt-4o-mini"          # Model for summarization
preserve_recent = 5                    # Keep N recent messages
```

## Tool Configuration

### Tool Loading

```toml
[agent.tools]
tool_modules = [                       # Python modules to scan
    "src.tools.built_in",
    "src.tools.custom"
]
tool_paths = [                         # JSON definition paths
    "config/tools/",
    "tools.json"
]
```

### Tool Validation

```toml
[agent.tools.validation]
enabled = true                         # Enable validation
max_param_length = 10000               # Max parameter length
timeout = 30                           # Tool timeout (seconds)
```

### Tool Execution

```toml
[agent.tools.execution]
parallel = true                        # Allow parallel execution
max_concurrent = 5                     # Max concurrent tools
retry_on_error = true                  # Retry failed tools
max_retries = 2                        # Max retry attempts
```

## MCP Configuration

### stdio Server

```toml
[[agent.mcp]]
name = "calculator"                    # Server identifier
type = "stdio"                         # Transport type
enabled = true                         # Enable/disable
command = "uvx"                        # Executable
args = ["mcp-server-calculator"]       # Arguments
env = { DEBUG = "false" }              # Environment
cwd = "/app"                           # Working directory
```

### HTTP Server

```toml
[[agent.mcp]]
name = "api-service"
type = "http"
enabled = true
url = "https://api.example.com/mcp"    # Server URL
headers = {                            # HTTP headers
    Authorization = "Bearer ${API_TOKEN}"
}
timeout = 30                           # Request timeout
```

### WebSocket Server

```toml
[[agent.mcp]]
name = "realtime"
type = "websocket"
enabled = true
url = "wss://api.example.com/mcp"      # WebSocket URL
headers = { "X-API-Key" = "${API_KEY}" }
ping_interval = 30                     # Keep-alive interval
```

### Stateful Sessions

```toml
[[agent.mcp]]
name = "erp-system"
type = "http"
enabled = true
url = "https://erp.example.com/mcp"
stateful = true                        # Enable sessions
session_header = "X-Session-Id"        # Session header name
requires_user_id = true                # Require user context

[agent.mcp_sessions]
enabled = true
session_ttl = 3600                     # Session TTL
persist_sessions = true                # Save to ADLS
```

## Security Configuration

### Rate Limiting

```toml
[agent.security.rate_limit]
enabled = true                         # Enable rate limiting
requests_per_minute = 60               # Requests per user/minute
requests_per_hour = 500                # Requests per user/hour
burst_size = 10                        # Burst allowance
```

### Input Validation

```toml
[agent.security.validation]
enabled = true                         # Enable validation
max_input_length = 10000               # Max input characters
detect_injection = true                # Detect prompt injection
blocked_patterns = [                   # Blocked regex patterns
    "ignore.*instructions",
    "system.*prompt"
]
```

### Output Filtering

```toml
[agent.security.output]
enabled = true                         # Enable output filtering
max_output_length = 50000              # Max output characters
redact_patterns = [                    # Patterns to redact
    "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
    "\\b\\d{3}-\\d{2}-\\d{4}\\b"
]
```

### Authentication

```toml
[agent.security.auth]
enabled = true                         # Enable auth
type = "azure_ad"                      # Auth type
tenant_id = ""                         # Azure AD tenant
client_id = ""                         # App client ID
required_scopes = ["api://agent/read"] # Required scopes
```

## Observability Configuration

### Tracing

```toml
[agent.observability]
tracing_enabled = true                 # Enable tracing
tracing_exporter = "jaeger"            # jaeger, azure, otlp
service_name = "msft-agent"            # Service name in traces

# Jaeger settings
jaeger_endpoint = "http://localhost:14268/api/traces"

# OTLP settings
otlp_endpoint = "http://localhost:4317"
otlp_protocol = "grpc"                 # grpc, http
```

### Metrics

```toml
[agent.observability]
metrics_enabled = true                 # Enable metrics
metrics_exporter = "prometheus"        # prometheus, azure, otlp
prometheus_port = 9090                 # Prometheus scrape port
```

### Logging

```toml
[agent.observability]
log_format = "json"                    # json, text
log_output = "stdout"                  # stdout, file
log_file = "logs/agent.log"            # If output=file
include_request_body = false           # Log request bodies
include_response_body = false          # Log response bodies
```

## Workflow Configuration

### Sequential Workflow

```toml
[agent.workflows.sequential]
enabled = true
steps = [
    { agent = "planner", input = "user_input" },
    { agent = "executor", input = "planner_output" },
    { agent = "reviewer", input = "executor_output" }
]
```

### Multi-Agent Settings

```toml
[agent.workflows]
max_agents = 10                        # Max agents in workflow
timeout = 300                          # Workflow timeout
allow_cycles = false                   # Allow cyclic workflows
```

## Server Configuration

### HTTP Server

```toml
[server]
host = "0.0.0.0"                       # Bind address
port = 8080                            # HTTP port
workers = 4                            # Uvicorn workers
timeout = 120                          # Request timeout
```

### Health Checks

```toml
[server.health]
enabled = true                         # Enable health endpoints
include_components = true              # Include component status
timeout = 10                           # Health check timeout
```

### CORS

```toml
[server.cors]
enabled = true                         # Enable CORS
allowed_origins = ["*"]                # Allowed origins
allowed_methods = ["GET", "POST"]      # Allowed methods
allowed_headers = ["*"]                # Allowed headers
```

## Complete Example

See `config/agent.toml.example` for a complete configuration example with all options.

## Environment Variable Overrides

Most settings can be overridden with environment variables:

```bash
# Format: AGENT_<SECTION>_<KEY>=value
AGENT_LOG_LEVEL=DEBUG
AGENT_MEMORY_CACHE_HOST=redis.example.com
AGENT_SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=120
```

See [Environment Variables](environment-variables.md) for the complete list.

## Related Documentation

- [Environment Variables](environment-variables.md) — Env var reference
- [Quick Start](../getting-started/quick-start.md) — Basic configuration
- [Security Guide](../guides/security.md) — Security configuration
