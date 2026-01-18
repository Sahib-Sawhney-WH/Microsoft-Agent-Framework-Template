# Production Readiness Checklist

A comprehensive checklist to verify your Microsoft Agent Framework deployment is production-ready.

## Quick Assessment

| Category | Status | Priority |
|----------|--------|----------|
| Security | [ ] | Critical |
| Reliability | [ ] | Critical |
| Observability | [ ] | High |
| Performance | [ ] | High |
| Operations | [ ] | Medium |
| Compliance | [ ] | Variable |

---

## Security

### Authentication & Authorization

- [ ] **Managed Identity configured** — Use Azure Managed Identity instead of secrets
  ```bash
  # Verify managed identity is assigned
  az vm identity show --resource-group myRG --name myVM
  ```

- [ ] **Service Principal scoped** — If using SP, use minimal required permissions
  ```bash
  # Check role assignments
  az role assignment list --assignee $SP_ID --output table
  ```

- [ ] **API authentication enabled** — Protect API endpoints
  - [ ] OAuth 2.0 / Azure AD authentication
  - [ ] API key validation (if applicable)
  - [ ] JWT token validation

- [ ] **Rate limiting enabled** — Prevent abuse
  ```toml
  [agent.security.rate_limit]
  enabled = true
  requests_per_minute = 60
  tokens_per_minute = 100000
  per_user = true
  ```

### Input Validation

- [ ] **Prompt injection protection enabled**
  ```toml
  [agent.security.validation]
  block_prompt_injection = true
  ```

- [ ] **Input length limits configured**
  ```toml
  [agent.security.validation]
  max_question_length = 32000
  max_tool_param_length = 10000
  ```

- [ ] **PII handling configured** (redact or block)
  ```toml
  [agent.security.validation]
  redact_pii = true
  ```

### Network Security

- [ ] **VNet integration** — Deploy in private VNet
- [ ] **Private endpoints** — Use private endpoints for Azure services
  - [ ] Azure OpenAI private endpoint
  - [ ] Redis private endpoint
  - [ ] Storage private endpoint
- [ ] **Network Security Groups** — Restrict inbound/outbound traffic
- [ ] **TLS 1.2+** — Enforce minimum TLS version
- [ ] **No public endpoints** — Disable public access where possible

### Secrets Management

- [ ] **Azure Key Vault** — Store secrets in Key Vault
  ```toml
  [agent.secrets]
  keyvault_url = "https://your-keyvault.vault.azure.net/"
  ```

- [ ] **No hardcoded secrets** — Verify no secrets in code or config
  ```bash
  # Scan for potential secrets
  grep -r "password\|secret\|key\|token" --include="*.py" --include="*.toml"
  ```

- [ ] **Environment variables reviewed** — No sensitive values in logs

### Container Security

- [ ] **Non-root user** — Container runs as non-root
- [ ] **Read-only filesystem** — Use read-only root filesystem
- [ ] **No privileged mode** — Container not running privileged
- [ ] **Image scanned** — Vulnerability scan passed
  ```bash
  trivy image msft-agent:latest --severity HIGH,CRITICAL
  ```

---

## Reliability

### High Availability

- [ ] **Multiple replicas** — At least 2 replicas in production
  ```yaml
  # Kubernetes
  spec:
    replicas: 3
  ```

- [ ] **Pod Disruption Budget** — Prevent all pods from being evicted
  ```yaml
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  spec:
    minAvailable: 1
  ```

- [ ] **Anti-affinity rules** — Spread pods across nodes/zones
  ```yaml
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            topologyKey: topology.kubernetes.io/zone
  ```

- [ ] **Multi-zone deployment** — Deploy across availability zones

### Health Checks

- [ ] **Liveness probe configured**
  ```yaml
  livenessProbe:
    httpGet:
      path: /health/live
      port: 8080
    initialDelaySeconds: 30
    periodSeconds: 10
  ```

- [ ] **Readiness probe configured**
  ```yaml
  readinessProbe:
    httpGet:
      path: /health/ready
      port: 8080
    initialDelaySeconds: 10
    periodSeconds: 5
  ```

- [ ] **Startup probe configured** (for slow-starting containers)
  ```yaml
  startupProbe:
    httpGet:
      path: /health/live
      port: 8080
    failureThreshold: 30
    periodSeconds: 10
  ```

### Resource Management

- [ ] **Resource requests set** — Guarantee minimum resources
  ```yaml
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
  ```

- [ ] **Resource limits set** — Prevent resource exhaustion
  ```yaml
  resources:
    limits:
      cpu: "2"
      memory: "4Gi"
  ```

- [ ] **Horizontal Pod Autoscaler** — Auto-scale based on load
  ```yaml
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

### Graceful Shutdown

- [ ] **Termination grace period** — Allow time for cleanup
  ```yaml
  terminationGracePeriodSeconds: 60
  ```

- [ ] **PreStop hook** — Drain connections before termination
  ```yaml
  lifecycle:
    preStop:
      exec:
        command: ["/bin/sh", "-c", "sleep 10"]
  ```

### Backup & Recovery

- [ ] **Session data backed up** — ADLS persistence enabled
  ```toml
  [agent.memory.persistence]
  enabled = true
  ```

- [ ] **Recovery tested** — Verified recovery from backup
- [ ] **RTO/RPO defined** — Recovery objectives documented

---

## Observability

### Logging

- [ ] **Structured logging** — JSON format logs
  ```toml
  [agent]
  log_level = "INFO"
  ```

- [ ] **Log aggregation** — Logs shipped to central system
  - [ ] Azure Monitor Logs
  - [ ] ELK Stack
  - [ ] Splunk

- [ ] **Log retention** — Retention policy configured
- [ ] **Sensitive data excluded** — No PII/secrets in logs

### Tracing

- [ ] **Distributed tracing enabled**
  ```toml
  [agent.observability]
  tracing_enabled = true
  tracing_exporter = "azure"  # or "otlp"
  ```

- [ ] **Trace sampling configured** — Appropriate sample rate
  ```toml
  [agent.observability]
  sample_rate = 0.1  # 10% sampling for high traffic
  ```

- [ ] **Correlation IDs** — Request correlation working

### Metrics

- [ ] **Metrics collection enabled**
  ```toml
  [agent.observability]
  metrics_enabled = true
  metrics_exporter = "prometheus"
  ```

- [ ] **Key metrics defined**
  - [ ] Request latency (p50, p95, p99)
  - [ ] Error rate
  - [ ] Token usage
  - [ ] Cache hit rate

- [ ] **Dashboards created** — Operational dashboards
- [ ] **SLIs defined** — Service Level Indicators documented

### Alerting

- [ ] **Alerts configured** — Critical alerts in place
  - [ ] Error rate > 1%
  - [ ] Latency p95 > 5s
  - [ ] Pod restarts > 3/hour
  - [ ] Memory usage > 80%

- [ ] **On-call rotation** — Team notified of alerts
- [ ] **Runbooks created** — Response procedures documented

---

## Performance

### Caching

- [ ] **Redis cache enabled** — Session caching active
  ```toml
  [agent.memory.cache]
  enabled = true
  ```

- [ ] **Cache TTL optimized** — Appropriate TTL values
- [ ] **Cache hit rate monitored** — Target > 80%

### Context Management

- [ ] **Summarization enabled** — Prevent context overflow
  ```toml
  [agent.memory.summarization]
  enabled = true
  max_tokens = 8000
  ```

- [ ] **Token limits configured** — Within model limits

### Connection Pooling

- [ ] **Redis connection pool** — Pooled connections
- [ ] **HTTP connection reuse** — Keep-alive enabled

### Load Testing

- [ ] **Load test completed** — Performance under load verified
- [ ] **Baseline established** — Normal performance documented
- [ ] **Capacity planned** — Scale requirements understood

---

## Operations

### CI/CD Pipeline

- [ ] **Automated builds** — CI pipeline configured
- [ ] **Automated tests** — Tests run on PR/merge
- [ ] **Security scanning** — SAST/DAST in pipeline
- [ ] **Automated deployment** — CD pipeline configured
- [ ] **Rollback tested** — Can quickly rollback

### Configuration Management

- [ ] **Config externalized** — No hardcoded config
- [ ] **Config versioned** — ConfigMaps/Secrets versioned
- [ ] **Environment parity** — Dev/staging/prod similar

### Documentation

- [ ] **Architecture documented** — System design documented
- [ ] **Runbooks created** — Operational procedures
- [ ] **API documented** — API reference available
- [ ] **Troubleshooting guide** — Common issues documented

### Change Management

- [ ] **Change process defined** — Review/approval process
- [ ] **Deployment windows** — Scheduled maintenance windows
- [ ] **Communication plan** — Stakeholder notification

---

## Compliance

### Data Handling

- [ ] **Data classification** — Data types identified
- [ ] **Data retention** — Retention policies implemented
- [ ] **Data encryption** — Encryption at rest and in transit
- [ ] **Data residency** — Geographic requirements met

### Audit & Governance

- [ ] **Audit logging** — Security events logged
- [ ] **Access reviews** — Periodic access reviews scheduled
- [ ] **Compliance controls** — Required controls implemented
  - [ ] SOC 2 (if applicable)
  - [ ] GDPR (if applicable)
  - [ ] HIPAA (if applicable)

---

## Final Verification

### Pre-Deploy Checks

```bash
# 1. Verify image builds successfully
docker build -t msft-agent:latest -f deployment/Dockerfile .

# 2. Run security scan
trivy image msft-agent:latest --severity HIGH,CRITICAL

# 3. Validate Kubernetes manifests
kubectl apply --dry-run=client -f deployment/kubernetes/

# 4. Run tests
pytest tests/ -v

# 5. Verify health endpoints
curl http://localhost:8080/health
```

### Post-Deploy Checks

```bash
# 1. Verify pods running
kubectl get pods -n msft-agent

# 2. Check logs for errors
kubectl logs -l app=msft-agent -n msft-agent --tail=100

# 3. Verify health check
kubectl exec -it deploy/msft-agent -n msft-agent -- curl localhost:8080/health

# 4. Test functionality
curl -X POST https://your-endpoint/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello, world!"}'

# 5. Verify metrics
curl http://localhost:8080/metrics
```

---

## Sign-Off

| Check | Reviewer | Date | Status |
|-------|----------|------|--------|
| Security Review | | | [ ] |
| Architecture Review | | | [ ] |
| Operations Review | | | [ ] |
| Compliance Review | | | [ ] |
| Final Approval | | | [ ] |

---

## Related Documentation

- [Kubernetes Deployment](kubernetes.md)
- [Security Guide](../guides/security.md)
- [Monitoring Guide](../operations/monitoring.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)
