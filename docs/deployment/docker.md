# Docker Deployment

This guide covers building and running the Microsoft Agent Framework with Docker.

## Prerequisites

- **Docker 20.10+** — Container runtime
- **Docker Compose v2** — Multi-container orchestration
- **Azure OpenAI resource** — With deployed model

## Quick Start

### Build and Run

```bash
# Build the image
docker build -t msft-agent:latest -f deployment/Dockerfile .

# Run with environment variables
docker run -d \
  --name msft-agent \
  -p 8080:8080 \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  msft-agent:latest

# Verify running
docker logs msft-agent
```

### Using Docker Compose (Recommended)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f agent

# Stop services
docker-compose down
```

## Dockerfile Overview

The project uses a multi-stage build for optimal image size:

```dockerfile
# Stage 1: Build
FROM python:3.12-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY pyproject.toml .
RUN pip install --user --no-cache-dir .

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY src/ ./src/
COPY config/ ./config/
CMD ["python", "-m", "src.orchestrator.main"]
```

**Image characteristics:**
- Base: `python:3.12-slim` (~150MB)
- Final size: ~500MB (with dependencies)
- Non-root capable (can run as non-root user)

## Building Images

### Development Build

```bash
# Standard build
docker build -t msft-agent:dev -f deployment/Dockerfile .

# Build with no cache (clean rebuild)
docker build --no-cache -t msft-agent:dev -f deployment/Dockerfile .
```

### Production Build

```bash
# Build with version tag
VERSION=$(git describe --tags --always)
docker build \
  -t msft-agent:${VERSION} \
  -t msft-agent:latest \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VERSION=${VERSION} \
  -f deployment/Dockerfile .
```

### Multi-Architecture Build

```bash
# Create builder (first time only)
docker buildx create --name multiarch --use

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myregistry.azurecr.io/msft-agent:latest \
  --push \
  -f deployment/Dockerfile .
```

## Running Containers

### Basic Run

```bash
docker run -d \
  --name msft-agent \
  -p 8080:8080 \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  msft-agent:latest
```

### With All Options

```bash
docker run -d \
  --name msft-agent \
  -p 8080:8080 \
  --restart unless-stopped \
  --memory 2g \
  --cpus 2 \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  -e REDIS_HOST="redis" \
  -e REDIS_PORT="6379" \
  -e LOG_LEVEL="INFO" \
  -v $(pwd)/config:/app/config:ro \
  --health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/health')\"" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 3 \
  msft-agent:latest
```

### With Azure Managed Identity

When running in Azure (VMs, Container Instances, etc.), use Managed Identity:

```bash
docker run -d \
  --name msft-agent \
  -p 8080:8080 \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  -e AZURE_CLIENT_ID="your-managed-identity-client-id" \
  msft-agent:latest
```

## Docker Compose

### Development Configuration

The included `docker-compose.yml` provides:

- **agent**: AI Assistant service
- **redis**: Session cache
- **jaeger**: Distributed tracing

```yaml
services:
  agent:
    build:
      context: .
      dockerfile: deployment/Dockerfile
    ports:
      - "8080:8080"
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}
      - REDIS_HOST=redis
    depends_on:
      - redis
      - jaeger

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  jaeger:
    image: jaegertracing/all-in-one:1.53
    ports:
      - "16686:16686"
      - "4317:4317"
```

### Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d agent

# View logs
docker-compose logs -f agent

# Restart service
docker-compose restart agent

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild and start
docker-compose up -d --build
```

### Override for Production

Create `docker-compose.override.yml` for environment-specific settings:

```yaml
# docker-compose.override.yml (production)
version: "3.8"

services:
  agent:
    image: myregistry.azurecr.io/msft-agent:v1.0.0
    build: !reset null
    environment:
      - LOG_LEVEL=WARNING
      - REDIS_HOST=your-redis.redis.cache.windows.net
      - REDIS_PORT=6380
      - REDIS_SSL=true
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # Remove development services
  redis: !reset null
  jaeger: !reset null
```

## Health Checks

### Built-in Health Endpoint

The agent exposes health endpoints:

```bash
# Full health check
curl http://localhost:8080/health

# Readiness probe (Kubernetes)
curl http://localhost:8080/health/ready

# Liveness probe (Kubernetes)
curl http://localhost:8080/health/live
```

### Docker Health Check

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' msft-agent

# View health check logs
docker inspect --format='{{json .State.Health}}' msft-agent | jq
```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://xxx.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_API_VERSION` | API version | `2024-10-01-preview` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_HOST` | Redis hostname | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_SSL` | Use SSL for Redis | `false` |
| `OTEL_SERVICE_NAME` | Service name for tracing | `ai-assistant` |

See [Environment Variables Reference](../reference/environment-variables.md) for complete list.

## Container Registry

### Push to Azure Container Registry

```bash
# Login to ACR
az acr login --name myregistry

# Tag image
docker tag msft-agent:latest myregistry.azurecr.io/msft-agent:v1.0.0

# Push image
docker push myregistry.azurecr.io/msft-agent:v1.0.0
```

### Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Tag and push
docker tag msft-agent:latest youruser/msft-agent:v1.0.0
docker push youruser/msft-agent:v1.0.0
```

## Security Best Practices

### Run as Non-Root

Add to Dockerfile:

```dockerfile
# Create non-root user
RUN useradd -m -u 1000 agent
USER agent
```

### Use Read-Only Filesystem

```bash
docker run -d \
  --read-only \
  --tmpfs /tmp \
  -v config:/app/config:ro \
  msft-agent:latest
```

### Scan for Vulnerabilities

```bash
# Using Trivy
trivy image msft-agent:latest

# Using Docker Scout
docker scout cves msft-agent:latest
```

### Limit Resources

```bash
docker run -d \
  --memory 2g \
  --memory-reservation 1g \
  --cpus 2 \
  --pids-limit 100 \
  msft-agent:latest
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs msft-agent

# Run interactively
docker run -it --rm msft-agent:latest /bin/bash

# Check environment
docker exec msft-agent env
```

### Health Check Failing

```bash
# Check health status
docker inspect msft-agent | jq '.[0].State.Health'

# Manual health check
docker exec msft-agent curl -s http://localhost:8080/health
```

### Memory Issues

```bash
# Check memory usage
docker stats msft-agent

# Increase memory limit
docker update --memory 4g msft-agent
```

## Next Steps

- [Kubernetes Deployment](kubernetes.md) — Deploy to Kubernetes
- [Azure Container Apps](azure-container-apps.md) — Serverless deployment
- [Production Checklist](production-checklist.md) — Pre-production verification
