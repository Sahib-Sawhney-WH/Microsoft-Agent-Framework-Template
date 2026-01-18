# Deployment Overview

This guide covers all deployment options for the Microsoft Agent Framework.

## Deployment Options Comparison

| Option | Best For | Complexity | Scalability | Cost |
|--------|----------|------------|-------------|------|
| **Local Development** | Development & testing | Low | N/A | Free |
| **Docker** | Single-server deployments | Low | Limited | Low |
| **Docker Compose** | Multi-container local dev | Low | Limited | Free |
| **Kubernetes** | Production workloads | Medium | High | Variable |
| **Azure Container Apps** | Azure-native serverless | Low | High | Pay-per-use |
| **Azure Kubernetes Service** | Enterprise production | High | Very High | Variable |

## Quick Start

### Option 1: Local Development (Fastest)

```bash
# Clone and install
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework
pip install -e .

# Configure
cp config/agent.toml.example config/agent.toml
# Edit config/agent.toml with your Azure OpenAI credentials

# Run
python -m src.agent.assistant
```

See [Local Development](local-development.md) for detailed instructions.

### Option 2: Docker Compose (Recommended for Development)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Start all services (agent + Redis + Jaeger)
docker-compose up -d

# View logs
docker-compose logs -f agent

# Access services
# Agent API: http://localhost:8080
# Jaeger UI: http://localhost:16686
```

See [Docker Deployment](docker.md) for detailed instructions.

### Option 3: Kubernetes (Production)

```bash
# Create namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# Deploy configuration
kubectl apply -f deployment/kubernetes/configmap.yaml
kubectl apply -f deployment/kubernetes/secret.yaml

# Deploy application
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/service.yaml
kubectl apply -f deployment/kubernetes/hpa.yaml
```

See [Kubernetes Deployment](kubernetes.md) for detailed instructions.

### Option 4: Azure Container Apps (Serverless)

```bash
# Deploy with Azure CLI
az containerapp up \
  --name msft-agent \
  --resource-group your-rg \
  --source . \
  --env-vars AZURE_OPENAI_ENDPOINT=... AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

See [Azure Container Apps](azure-container-apps.md) for detailed instructions.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                    (Ingress / Azure Front Door)                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Service                               │
│                  (Kubernetes Pods / Container Apps)              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    Pod 1        │  │    Pod 2        │  │    Pod N        │  │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │  │
│  │  │   Agent   │  │  │  │   Agent   │  │  │  │   Agent   │  │  │
│  │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Azure OpenAI    │  │   Azure Redis     │  │   Azure Blob      │
│   (LLM Backend)   │  │   (Session Cache) │  │   (Persistence)   │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

## Deployment Guides

| Guide | Description |
|-------|-------------|
| [Local Development](local-development.md) | Set up local development environment |
| [Docker](docker.md) | Build and run Docker containers |
| [Kubernetes](kubernetes.md) | Deploy to Kubernetes cluster |
| [Azure Container Apps](azure-container-apps.md) | Deploy to Azure Container Apps |
| [Azure Setup](azure-setup.md) | Configure Azure resources |
| [Production Checklist](production-checklist.md) | Pre-production verification |

## Environment Requirements

### Minimum Requirements

| Component | Development | Production |
|-----------|-------------|------------|
| CPU | 1 core | 2+ cores |
| Memory | 512 MB | 2+ GB |
| Python | 3.10+ | 3.10+ |
| Azure OpenAI | Required | Required |

### Recommended Requirements

| Component | Development | Production |
|-----------|-------------|------------|
| CPU | 2 cores | 4+ cores |
| Memory | 2 GB | 4+ GB |
| Redis | Local container | Azure Cache for Redis |
| Storage | Local filesystem | Azure Blob Storage |
| Monitoring | Jaeger local | Azure Monitor |

## Security Considerations

Before deploying to production, review:

1. **Authentication**: Configure managed identity or service principal
2. **Network Security**: Set up VNet integration and private endpoints
3. **Secrets Management**: Use Azure Key Vault for sensitive values
4. **Rate Limiting**: Enable and configure rate limits
5. **Input Validation**: Ensure prompt injection protection is enabled

See [Production Checklist](production-checklist.md) for complete verification steps.

## Related Documentation

- [Architecture Overview](../architecture/index.md)
- [Configuration Reference](../reference/configuration-reference.md)
- [Environment Variables](../reference/environment-variables.md)
- [Security Guide](../guides/security.md)
- [Monitoring & Observability](../operations/monitoring.md)
