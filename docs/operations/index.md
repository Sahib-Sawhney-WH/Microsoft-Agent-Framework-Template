# Operations Guide

Day-to-day operations for running the Microsoft Agent Framework in production.

## Quick Links

| Guide | Description |
|-------|-------------|
| [Monitoring](monitoring.md) | Dashboards, alerts, and metrics |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |
| [Scaling](scaling.md) | Handle increased load |

## Operational Overview

### Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Request latency (p95) | < 2s | > 5s |
| Error rate | < 1% | > 5% |
| Cache hit rate | > 80% | < 50% |
| Pod memory usage | < 70% | > 85% |
| Token usage | Within budget | Approaching limit |

### Daily Operations

1. **Check dashboards** for anomalies
2. **Review error logs** for new issues
3. **Monitor resource usage** trends
4. **Verify backup completion** (if ADLS persistence enabled)

### Weekly Operations

1. **Review security alerts** and blocked requests
2. **Analyze slow queries** and optimize
3. **Check cost trends** in Azure
4. **Update documentation** for any changes

### Monthly Operations

1. **Security audit** of access permissions
2. **Capacity planning** review
3. **Dependency updates** (security patches)
4. **DR drill** (if applicable)

## Health Endpoints

### Readiness Probe

```bash
curl http://localhost:8080/health/ready
```

Returns `200 OK` when the service is ready to receive traffic.

### Liveness Probe

```bash
curl http://localhost:8080/health/live
```

Returns `200 OK` when the service is alive (should be restarted if fails).

### Full Health Check

```bash
curl http://localhost:8080/health
```

Returns detailed component health:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "components": [
    {"name": "redis", "status": "healthy", "latency_ms": 2.5},
    {"name": "adls", "status": "healthy", "latency_ms": 45.2},
    {"name": "llm", "status": "healthy", "latency_ms": 150.0}
  ]
}
```

## Log Analysis

### Log Locations

| Environment | Location |
|-------------|----------|
| Local | stdout/stderr |
| Docker | `docker logs msft-agent` |
| Kubernetes | `kubectl logs -l app=msft-agent` |
| Azure | Azure Monitor Logs |

### Important Log Patterns

```bash
# Errors
grep -E "ERROR|Exception|Failed" logs.txt

# Rate limiting
grep "RateLimitExceeded" logs.txt

# Security events
grep -E "injection|blocked|validation" logs.txt

# Slow requests
grep "latency.*[5-9][0-9]{3}|[0-9]{5,}" logs.txt
```

### Structured Log Queries (Azure)

```kusto
// Error rate over time
traces
| where severityLevel >= 3
| summarize count() by bin(timestamp, 1h)
| render timechart

// Slow requests
requests
| where duration > 5000
| project timestamp, name, duration, success
| order by duration desc
```

## Alerting

### Critical Alerts (PagerDuty)

| Alert | Condition | Action |
|-------|-----------|--------|
| Service Down | Health check fails 3x | Immediate investigation |
| Error Spike | Error rate > 10% for 5 min | Check logs, rollback if needed |
| High Latency | p95 > 10s for 10 min | Check LLM quotas, scale up |

### Warning Alerts (Email/Slack)

| Alert | Condition | Action |
|-------|-----------|--------|
| Memory High | Usage > 80% | Monitor, plan scaling |
| Cache Miss Rate | > 50% for 30 min | Check Redis, tune TTL |
| Token Quota | > 80% of limit | Review usage, increase quota |

## Runbooks

### Service Restart

```bash
# Kubernetes
kubectl rollout restart deployment/msft-agent -n msft-agent

# Docker Compose
docker-compose restart agent

# Azure Container Apps
az containerapp revision restart --name msft-agent --resource-group myRG
```

### Scale Up

```bash
# Kubernetes
kubectl scale deployment/msft-agent --replicas=5 -n msft-agent

# Azure Container Apps
az containerapp update --name msft-agent --resource-group myRG --max-replicas 10
```

### Rollback

```bash
# Kubernetes
kubectl rollout undo deployment/msft-agent -n msft-agent

# Verify rollback
kubectl rollout status deployment/msft-agent -n msft-agent
```

## Related Documentation

- [Monitoring](monitoring.md) — Detailed monitoring setup
- [Troubleshooting](troubleshooting.md) — Issue resolution
- [Scaling](scaling.md) — Capacity management
- [Production Checklist](../deployment/production-checklist.md) — Pre-production verification
