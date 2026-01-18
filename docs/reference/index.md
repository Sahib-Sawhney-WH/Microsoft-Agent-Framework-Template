# Reference Documentation

Technical reference for the Microsoft Agent Framework.

## Quick Links

| Reference | Description |
|-----------|-------------|
| [Configuration Reference](configuration-reference.md) | All configuration options |
| [Environment Variables](environment-variables.md) | Environment variable reference |

## Configuration Files

### Primary Configuration

| File | Purpose |
|------|---------|
| `config/agent.toml` | Main agent configuration |
| `.env` | Environment variables |
| `deployment/kubernetes/*.yaml` | Kubernetes manifests |

### Configuration Priority

Environment variables override TOML configuration:

```
Environment Variables (highest priority)
    ↓
config/agent.toml
    ↓
Default Values (lowest priority)
```

## API Reference

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Full health check with components |
| `/health/ready` | GET | Readiness probe |
| `/health/live` | GET | Liveness probe |

### Chat API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/question` | POST | Process a question |
| `/api/chat` | POST | Chat with history |
| `/api/sessions/{id}` | GET | Get session info |
| `/api/sessions/{id}` | DELETE | End session |

### Request Format

```json
{
  "question": "What is the weather?",
  "user_id": "user-123",
  "chat_id": "chat-456",
  "context": {
    "key": "value"
  }
}
```

### Response Format

```json
{
  "answer": "The weather is...",
  "chat_id": "chat-456",
  "tokens": {
    "input": 150,
    "output": 200
  },
  "tool_calls": [
    {
      "name": "weather_lookup",
      "arguments": {"location": "Seattle"}
    }
  ],
  "latency_ms": 1500
}
```

## Tool Schema

### Tool Definition

```python
@register_tool(
    name="my_tool",
    description="Tool description for the LLM",
    enabled=True
)
def my_tool(param: str, optional_param: int = 10) -> str:
    """
    Docstring provides additional context.

    Args:
        param: Required parameter
        optional_param: Optional with default

    Returns:
        Tool result string
    """
    return f"Result: {param}"
```

### JSON Schema Format

```json
{
  "name": "my_tool",
  "description": "Tool description for the LLM",
  "parameters": {
    "type": "object",
    "properties": {
      "param": {
        "type": "string",
        "description": "Required parameter"
      },
      "optional_param": {
        "type": "integer",
        "description": "Optional with default",
        "default": 10
      }
    },
    "required": ["param"]
  }
}
```

## MCP Protocol Reference

### Tool Call Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param": "value"
    }
  },
  "id": 1
}
```

### Tool Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool result"
      }
    ]
  },
  "id": 1
}
```

## Metrics Reference

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ai_assistant_requests_total` | Counter | success, model | Total requests |
| `ai_assistant_request_latency_ms` | Histogram | model | Request latency |
| `ai_assistant_errors_total` | Counter | error_type | Error count |
| `ai_assistant_tool_calls_total` | Counter | tool_name, success | Tool invocations |
| `ai_assistant_tokens_total` | Counter | type, model | Token usage |
| `ai_assistant_cache_hits_total` | Counter | cache_type | Cache hits |
| `ai_assistant_cache_misses_total` | Counter | cache_type | Cache misses |
| `ai_assistant_active_sessions` | Gauge | - | Active sessions |

### Prometheus Queries

```promql
# Request rate
rate(ai_assistant_requests_total[5m])

# Error rate percentage
sum(rate(ai_assistant_errors_total[5m])) / sum(rate(ai_assistant_requests_total[5m])) * 100

# P95 latency
histogram_quantile(0.95, rate(ai_assistant_request_latency_ms_bucket[5m]))

# Token usage per minute
rate(ai_assistant_tokens_total[1m]) * 60

# Cache hit rate
sum(rate(ai_assistant_cache_hits_total[5m])) / (sum(rate(ai_assistant_cache_hits_total[5m])) + sum(rate(ai_assistant_cache_misses_total[5m]))) * 100
```

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| `AUTH_001` | Authentication Failed | Azure credential issue |
| `AUTH_002` | Token Expired | Refresh required |
| `RATE_001` | Rate Limit Exceeded | Too many requests |
| `RATE_002` | Token Quota Exceeded | Azure OpenAI quota |
| `VAL_001` | Input Validation Failed | Invalid input |
| `VAL_002` | Prompt Injection Detected | Security block |
| `TOOL_001` | Tool Not Found | Unknown tool |
| `TOOL_002` | Tool Execution Failed | Tool error |
| `MCP_001` | MCP Connection Failed | Server unreachable |
| `MCP_002` | MCP Session Lost | Session expired |

## Related Documentation

- [Configuration Reference](configuration-reference.md) — All config options
- [Environment Variables](environment-variables.md) — Env var reference
- [Troubleshooting](../operations/troubleshooting.md) — Error resolution
