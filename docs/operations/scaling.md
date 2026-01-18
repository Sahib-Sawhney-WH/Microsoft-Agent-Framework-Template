# Scaling Guide

Handle increased load and plan for growth with the Microsoft Agent Framework.

## Scaling Dimensions

| Dimension | Metric | Scaling Approach |
|-----------|--------|------------------|
| **Requests** | Requests/second | Horizontal pod scaling |
| **Tokens** | Tokens/minute | Azure OpenAI quota |
| **Sessions** | Concurrent users | Redis scaling |
| **Storage** | History volume | Blob storage tiers |

## Horizontal Scaling

### Kubernetes HPA

The framework includes an HPA configuration:

```yaml
# deployment/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Tune for your workload:**

```yaml
# High traffic, fast scaling
spec:
  minReplicas: 3
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15

# Steady traffic, cost-optimized
spec:
  minReplicas: 2
  maxReplicas: 5
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 600
```

### Azure Container Apps

```bash
# Update scaling rules
az containerapp update \
  --name msft-agent \
  --resource-group myRG \
  --min-replicas 2 \
  --max-replicas 20 \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50
```

### Manual Scaling

```bash
# Kubernetes
kubectl scale deployment/msft-agent --replicas=5 -n msft-agent

# Docker Compose (with Swarm)
docker service scale msft-agent=5
```

## Azure OpenAI Scaling

### Check Current Quota

```bash
az cognitiveservices account show \
  --name your-openai \
  --resource-group your-rg \
  --query "properties.quotaLimit"
```

### Request Quota Increase

1. Go to Azure Portal > Azure OpenAI > Quotas
2. Select your deployment
3. Click "Request quota increase"

### Multi-Deployment Strategy

Distribute load across multiple deployments:

```toml
[[agent.models]]
name = "gpt-4o-1"
provider = "azure_openai"
endpoint = "https://region1.openai.azure.com/"
deployment = "gpt-4o"

[[agent.models]]
name = "gpt-4o-2"
provider = "azure_openai"
endpoint = "https://region2.openai.azure.com/"
deployment = "gpt-4o"
```

Implement load balancing in your application:

```python
import random

models = ["gpt-4o-1", "gpt-4o-2"]
selected_model = random.choice(models)
result = await assistant.process_question(question, model=selected_model)
```

### Rate Limit Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def process_with_retry(assistant, question):
    return await assistant.process_question(question)
```

## Redis Scaling

### Check Current Usage

```bash
# Azure Redis
az redis list-keys --name your-redis --resource-group your-rg

# Connect and check
redis-cli -h your-redis.redis.cache.windows.net -p 6380 --tls INFO memory
```

### Scaling Options

| Tier | Max Memory | Use Case |
|------|------------|----------|
| Basic | 250 MB | Development |
| Standard | 53 GB | Small production |
| Premium | 120 GB | High availability |
| Enterprise | 1.5 TB | Large scale |

### Scale Up

```bash
az redis update \
  --name your-redis \
  --resource-group your-rg \
  --sku Premium \
  --vm-size P2
```

### Clustering (Premium/Enterprise)

```bash
az redis create \
  --name your-redis-cluster \
  --resource-group your-rg \
  --sku Premium \
  --vm-size P1 \
  --shard-count 3
```

### Connection Pooling

```python
# Configure connection pool size
[agent.memory.cache]
max_connections = 100
min_connections = 10
```

## Storage Scaling

### Blob Storage Performance

| Tier | Latency | Cost | Use Case |
|------|---------|------|----------|
| Hot | Low | High | Active sessions |
| Cool | Medium | Medium | Recent history |
| Archive | High | Low | Long-term archive |

### Lifecycle Management

```json
{
  "rules": [
    {
      "name": "archiveOldSessions",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "tierToCool": { "daysAfterModificationGreaterThan": 30 },
            "tierToArchive": { "daysAfterModificationGreaterThan": 90 }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["chat-history/threads/"]
        }
      }
    }
  ]
}
```

### Premium Storage (High Performance)

For high-throughput requirements:

```bash
az storage account create \
  --name yourstorageaccount \
  --resource-group your-rg \
  --sku Premium_LRS \
  --kind BlockBlobStorage
```

## Capacity Planning

### Estimate Resource Needs

| Metric | Formula |
|--------|---------|
| Pods | `(requests/sec) / (requests/pod/sec)` |
| Memory | `(concurrent_sessions) * (avg_session_size)` |
| Redis | `(active_sessions) * (avg_session_size)` |
| Tokens | `(requests/min) * (avg_tokens/request)` |

### Example Calculation

For 1000 concurrent users:
- **Pods:** 1000 users / 100 requests/pod = 10 pods
- **Memory:** 10 pods * 2 GB = 20 GB
- **Redis:** 1000 sessions * 10 KB = 10 MB + overhead = 256 MB tier
- **Tokens:** 100 req/min * 1000 tokens = 100K tokens/min

### Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def ask_question(self):
        self.client.post("/api/question", json={
            "question": "What is AI?",
            "user_id": self.user_id
        })
```

```bash
locust -f locustfile.py --host=http://localhost:8080 --users=100 --spawn-rate=10
```

## Multi-Region Deployment

### Architecture

```
                    ┌─────────────────┐
                    │  Azure Front    │
                    │     Door        │
                    └────────┬────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
    ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
    │   East US      │ │   West EU      │ │   East Asia    │
    │   Cluster      │ │   Cluster      │ │   Cluster      │
    └────────────────┘ └────────────────┘ └────────────────┘
             │               │               │
             ▼               ▼               ▼
    ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
    │   Regional     │ │   Regional     │ │   Regional     │
    │   Resources    │ │   Resources    │ │   Resources    │
    └────────────────┘ └────────────────┘ └────────────────┘
```

### Configuration

```bash
# Deploy to multiple regions
for region in eastus westeurope eastasia; do
  az aks create --name msft-agent-$region --location $region ...
done

# Configure Azure Front Door
az afd endpoint create --profile-name msft-agent-afd --endpoint-name global ...
```

## Cost Optimization

### Right-Sizing

- Start with smaller instances
- Monitor actual usage
- Scale based on metrics

### Reserved Capacity

- Azure Reserved Instances (1-3 year)
- Committed use discounts

### Spot Instances

For non-critical workloads:

```yaml
# Kubernetes tolerations for spot nodes
tolerations:
  - key: "kubernetes.azure.com/scalesetpriority"
    operator: "Equal"
    value: "spot"
    effect: "NoSchedule"
```

## Related Documentation

- [Monitoring Guide](monitoring.md) — Track scaling metrics
- [Kubernetes Deployment](../deployment/kubernetes.md) — K8s configuration
- [Azure Setup](../deployment/azure-setup.md) — Azure resource configuration
