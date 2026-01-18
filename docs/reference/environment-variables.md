# Environment Variables Reference

Complete reference for all environment variables used by the Microsoft Agent Framework.

## Quick Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | No* | API key (if not using AAD) |
| `REDIS_HOST` | No | Redis hostname |
| `AZURE_STORAGE_ACCOUNT` | No | Storage account name |

*Required if not using DefaultAzureCredential

## Azure OpenAI

### Required

| Variable | Example | Description |
|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` | Azure OpenAI resource endpoint |

### Optional (API Key Auth)

| Variable | Example | Description |
|----------|---------|-------------|
| `AZURE_OPENAI_API_KEY` | `abc123...` | API key for Azure OpenAI |

### Optional (AAD Auth)

| Variable | Example | Description |
|----------|---------|-------------|
| `AZURE_CLIENT_ID` | `00000000-0000-0000-0000-000000000000` | Service principal client ID |
| `AZURE_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | Azure AD tenant ID |
| `AZURE_CLIENT_SECRET` | `secret...` | Service principal secret |

**Note:** For Managed Identity, only set `AZURE_CLIENT_ID` if using user-assigned identity.

## Redis Cache

### Local Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | (none) | Redis password |
| `REDIS_SSL` | `false` | Enable SSL/TLS |
| `REDIS_DB` | `0` | Redis database number |

### Azure Cache for Redis

| Variable | Example | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `your-redis.redis.cache.windows.net` | Azure Redis hostname |
| `REDIS_PORT` | `6380` | SSL port (always 6380) |
| `REDIS_SSL` | `true` | Must be true for Azure |
| `REDIS_USE_AZURE_AUTH` | `true` | Use AAD authentication |

**Example:**
```bash
export REDIS_HOST="your-redis.redis.cache.windows.net"
export REDIS_PORT="6380"
export REDIS_SSL="true"
export REDIS_USE_AZURE_AUTH="true"
```

## Azure Storage

### Blob Storage / ADLS

| Variable | Example | Description |
|----------|---------|-------------|
| `AZURE_STORAGE_ACCOUNT` | `yourstorageaccount` | Storage account name |
| `AZURE_STORAGE_CONTAINER` | `chat-history` | Blob container name |
| `AZURE_STORAGE_CONNECTION_STRING` | (optional) | Full connection string |

**Note:** Use `AZURE_STORAGE_ACCOUNT` with DefaultAzureCredential (recommended) or `AZURE_STORAGE_CONNECTION_STRING` for key-based auth.

## Observability

### Application Insights

| Variable | Example | Description |
|----------|---------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `InstrumentationKey=...` | App Insights connection |

### OpenTelemetry

| Variable | Example | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` | Protocol (grpc/http) |
| `OTEL_SERVICE_NAME` | `msft-agent` | Service name in traces |

### Jaeger

| Variable | Example | Description |
|----------|---------|-------------|
| `JAEGER_ENDPOINT` | `http://localhost:14268/api/traces` | Jaeger collector endpoint |
| `JAEGER_AGENT_HOST` | `localhost` | Jaeger agent hostname |
| `JAEGER_AGENT_PORT` | `6831` | Jaeger agent UDP port |

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server port |
| `WORKERS` | `4` | Number of workers |
| `LOG_LEVEL` | `INFO` | Logging level |

## MCP Server Secrets

Use environment variables for MCP server authentication:

| Variable | Example | Description |
|----------|---------|-------------|
| `MCP_API_TOKEN` | `token...` | Generic API token |
| `GITHUB_TOKEN` | `ghp_...` | GitHub personal access token |
| `BRAVE_API_KEY` | `BSA...` | Brave Search API key |
| `DATABASE_URL` | `postgresql://...` | Database connection string |

**Usage in config:**
```toml
[[agent.mcp]]
name = "github"
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }
```

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_RPM` | `60` | Requests per minute |
| `INPUT_VALIDATION_ENABLED` | `true` | Enable input validation |

## Development

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `RELOAD` | `false` | Enable auto-reload |
| `CONFIG_PATH` | `config/agent.toml` | Config file path |

## Docker Environment

When running with Docker, set variables in `.env` or `docker-compose.yml`:

### .env File

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here

# Redis (local)
REDIS_HOST=redis
REDIS_PORT=6379

# Storage (optional)
AZURE_STORAGE_ACCOUNT=yourstorageaccount
AZURE_STORAGE_CONTAINER=chat-history

# Observability
JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Server
PORT=8080
LOG_LEVEL=INFO
```

### docker-compose.yml

```yaml
services:
  agent:
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

## Kubernetes Environment

### ConfigMap (Non-Sensitive)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: msft-agent-config
data:
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  LOG_LEVEL: "INFO"
  OTEL_SERVICE_NAME: "msft-agent"
```

### Secret (Sensitive)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: msft-agent-secrets
type: Opaque
stringData:
  AZURE_OPENAI_ENDPOINT: "https://..."
  AZURE_OPENAI_API_KEY: "..."
```

### Deployment Reference

```yaml
spec:
  containers:
    - name: agent
      envFrom:
        - configMapRef:
            name: msft-agent-config
        - secretRef:
            name: msft-agent-secrets
```

## Azure Container Apps

```bash
az containerapp update \
  --name msft-agent \
  --resource-group myRG \
  --set-env-vars \
    "AZURE_OPENAI_ENDPOINT=https://..." \
    "REDIS_HOST=redis.redis.cache.windows.net" \
    "REDIS_PORT=6380" \
    "REDIS_SSL=true" \
    "REDIS_USE_AZURE_AUTH=true"
```

## Best Practices

### 1. Never Commit Secrets

```bash
# .gitignore
.env
*.env.local
secrets/
```

### 2. Use Secret Managers

**Azure Key Vault:**
```bash
az keyvault secret set --vault-name myVault --name "AZURE-OPENAI-KEY" --value "..."
```

**Kubernetes External Secrets:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
spec:
  secretStoreRef:
    name: azure-keyvault
  target:
    name: msft-agent-secrets
  data:
    - secretKey: AZURE_OPENAI_API_KEY
      remoteRef:
        key: AZURE-OPENAI-KEY
```

### 3. Environment-Specific Files

```
.env.development    # Local development
.env.staging        # Staging environment
.env.production     # Production (never commit)
```

### 4. Validation

```bash
# Check required variables
required_vars=("AZURE_OPENAI_ENDPOINT")
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var is not set"
    exit 1
  fi
done
```

## Troubleshooting

### Variable Not Loaded

```bash
# Check if variable is set
echo $AZURE_OPENAI_ENDPOINT

# Check .env is loaded (Python)
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('AZURE_OPENAI_ENDPOINT'))"
```

### Docker Variable Issues

```bash
# Check environment in container
docker exec msft-agent env | grep AZURE

# Check compose interpolation
docker-compose config
```

### Kubernetes Variable Issues

```bash
# Check pod environment
kubectl exec -it deploy/msft-agent -- env | grep AZURE

# Check secret exists
kubectl get secret msft-agent-secrets -o yaml
```

## Related Documentation

- [Configuration Reference](configuration-reference.md) — TOML configuration
- [Local Development](../deployment/local-development.md) — Development setup
- [Docker Deployment](../deployment/docker.md) — Docker configuration
- [Kubernetes Deployment](../deployment/kubernetes.md) — K8s configuration
