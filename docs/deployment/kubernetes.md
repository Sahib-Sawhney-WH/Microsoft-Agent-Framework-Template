# Kubernetes Deployment

This guide covers deploying the Microsoft Agent Framework to Kubernetes.

## Prerequisites

- **Kubernetes cluster** (1.24+) — AKS, EKS, GKE, or self-managed
- **kubectl** — Configured with cluster access
- **Container registry** — ACR, Docker Hub, or other registry
- **Azure OpenAI resource** — With deployed model

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Kubernetes Cluster                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        msft-agent Namespace                        │  │
│  │                                                                    │  │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │  │
│  │  │   Ingress   │────▶│   Service   │────▶│ Deployment  │         │  │
│  │  │  (NGINX/    │     │ (ClusterIP) │     │  (3 pods)   │         │  │
│  │  │   Azure)    │     └─────────────┘     └──────┬──────┘         │  │
│  │  └─────────────┘                                │                 │  │
│  │                                                 │                 │  │
│  │  ┌─────────────┐     ┌─────────────┐           │                 │  │
│  │  │  ConfigMap  │◀────┤             │◀──────────┘                 │  │
│  │  └─────────────┘     │    Pods     │                             │  │
│  │  ┌─────────────┐     │             │                             │  │
│  │  │   Secret    │◀────┤             │                             │  │
│  │  └─────────────┘     └─────────────┘                             │  │
│  │                                                                    │  │
│  │  ┌─────────────┐                                                  │  │
│  │  │     HPA     │ ─── Auto-scaling based on CPU/Memory             │  │
│  │  └─────────────┘                                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │Azure OpenAI │ │ Azure Redis │ │ Azure Blob  │
            │  (External) │ │  (External) │ │  (External) │
            └─────────────┘ └─────────────┘ └─────────────┘
```

## Quick Start

### 1. Push Image to Registry

```bash
# Build image
docker build -t msft-agent:latest -f deployment/Dockerfile .

# Tag for ACR
docker tag msft-agent:latest myregistry.azurecr.io/msft-agent:v1.0.0

# Login to ACR
az acr login --name myregistry

# Push image
docker push myregistry.azurecr.io/msft-agent:v1.0.0
```

### 2. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# Deploy configuration
kubectl apply -f deployment/kubernetes/configmap.yaml

# Deploy secrets (edit first!)
kubectl apply -f deployment/kubernetes/secret.yaml

# Deploy application
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/service.yaml
kubectl apply -f deployment/kubernetes/hpa.yaml

# Optional: Deploy ingress
kubectl apply -f deployment/kubernetes/ingress.yaml
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n msft-agent

# Check logs
kubectl logs -l app=msft-agent -n msft-agent --tail=50

# Port forward for testing
kubectl port-forward svc/msft-agent 8080:80 -n msft-agent

# Test health endpoint
curl http://localhost:8080/health
```

## Manifest Reference

### Namespace

```yaml
# deployment/kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: msft-agent
  labels:
    app.kubernetes.io/name: msft-agent
    app.kubernetes.io/part-of: ai-platform
```

### ConfigMap

```yaml
# deployment/kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: msft-agent-config
  namespace: msft-agent
data:
  AZURE_OPENAI_DEPLOYMENT: "gpt-4o"
  AZURE_OPENAI_API_VERSION: "2024-10-01-preview"
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  REDIS_PORT: "6380"
  REDIS_SSL: "true"
  REDIS_TTL: "3600"
  OTEL_SERVICE_NAME: "msft-agent"
```

### Secret

```yaml
# deployment/kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: msft-agent-secrets
  namespace: msft-agent
type: Opaque
stringData:
  AZURE_OPENAI_ENDPOINT: "https://your-resource.openai.azure.com/"
  REDIS_HOST: "your-redis.redis.cache.windows.net"
  STORAGE_ACCOUNT_NAME: "yourstorageaccount"
  # For Service Principal auth (if not using Managed Identity)
  # AZURE_CLIENT_ID: "your-client-id"
  # AZURE_TENANT_ID: "your-tenant-id"
  # AZURE_CLIENT_SECRET: "your-client-secret"
```

### Deployment

```yaml
# deployment/kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: msft-agent
  namespace: msft-agent
  labels:
    app: msft-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: msft-agent
  template:
    metadata:
      labels:
        app: msft-agent
    spec:
      serviceAccountName: msft-agent
      containers:
        - name: agent
          image: myregistry.azurecr.io/msft-agent:v1.0.0
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: msft-agent-config
            - secretRef:
                name: msft-agent-secrets
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: msft-agent
                topologyKey: topology.kubernetes.io/zone
```

### Service

```yaml
# deployment/kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: msft-agent
  namespace: msft-agent
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
      name: http
  selector:
    app: msft-agent
```

### Ingress

```yaml
# deployment/kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: msft-agent
  namespace: msft-agent
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - agent.example.com
      secretName: msft-agent-tls
  rules:
    - host: agent.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: msft-agent
                port:
                  number: 80
```

### Horizontal Pod Autoscaler

```yaml
# deployment/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: msft-agent
  namespace: msft-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: msft-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

## Azure Kubernetes Service (AKS)

### Create AKS Cluster

```bash
# Create resource group
az group create --name msft-agent-rg --location eastus

# Create AKS cluster with managed identity
az aks create \
  --resource-group msft-agent-rg \
  --name msft-agent-aks \
  --node-count 3 \
  --enable-managed-identity \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group msft-agent-rg --name msft-agent-aks
```

### Configure ACR Integration

```bash
# Attach ACR to AKS
az aks update \
  --resource-group msft-agent-rg \
  --name msft-agent-aks \
  --attach-acr myregistry
```

### Configure Workload Identity

```bash
# Enable workload identity
az aks update \
  --resource-group msft-agent-rg \
  --name msft-agent-aks \
  --enable-oidc-issuer \
  --enable-workload-identity

# Create managed identity
az identity create \
  --name msft-agent-identity \
  --resource-group msft-agent-rg

# Get identity details
CLIENT_ID=$(az identity show --name msft-agent-identity --resource-group msft-agent-rg --query clientId -o tsv)
```

### Service Account with Workload Identity

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: msft-agent
  namespace: msft-agent
  annotations:
    azure.workload.identity/client-id: "<your-client-id>"
  labels:
    azure.workload.identity/use: "true"
```

## Monitoring

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: msft-agent
  namespace: msft-agent
spec:
  selector:
    matchLabels:
      app: msft-agent
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Grafana Dashboard

Import the following metrics into Grafana:

- `ai_assistant_requests_total` — Request count
- `ai_assistant_request_latency_milliseconds` — Request latency
- `ai_assistant_errors_total` — Error count
- `ai_assistant_tool_calls_total` — Tool call count

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod -l app=msft-agent -n msft-agent

# Check events
kubectl get events -n msft-agent --sort-by='.lastTimestamp'

# Check logs
kubectl logs -l app=msft-agent -n msft-agent --previous
```

### Image Pull Errors

```bash
# Verify ACR access
az acr login --name myregistry

# Check image pull secret
kubectl get secrets -n msft-agent
kubectl describe secret acr-secret -n msft-agent
```

### Health Check Failures

```bash
# Exec into pod
kubectl exec -it deploy/msft-agent -n msft-agent -- /bin/sh

# Manual health check
curl localhost:8080/health

# Check environment
env | grep AZURE
```

### Resource Issues

```bash
# Check resource usage
kubectl top pods -n msft-agent

# Check HPA status
kubectl describe hpa msft-agent -n msft-agent

# Check node capacity
kubectl describe nodes | grep -A 5 "Allocated resources"
```

## Security Best Practices

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: msft-agent-network-policy
  namespace: msft-agent
spec:
  podSelector:
    matchLabels:
      app: msft-agent
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
```

### Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: msft-agent
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Related Documentation

- [Docker Deployment](docker.md)
- [Azure Container Apps](azure-container-apps.md)
- [Production Checklist](production-checklist.md)
- [Monitoring Guide](../operations/monitoring.md)
