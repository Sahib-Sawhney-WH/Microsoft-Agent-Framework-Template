# Monitoring Guide

Set up comprehensive monitoring for the Microsoft Agent Framework.

## Monitoring Stack

### Recommended Setup

| Component | Purpose | Options |
|-----------|---------|---------|
| **Metrics** | Performance tracking | Prometheus, Azure Monitor |
| **Tracing** | Request flow | Jaeger, Azure Application Insights |
| **Logging** | Error analysis | ELK, Azure Log Analytics |
| **Alerting** | Incident response | Alertmanager, Azure Alerts |

## Metrics

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `ai_assistant_requests_total` | Total requests | - |
| `ai_assistant_request_latency_ms` | Request latency | p95 < 2s |
| `ai_assistant_errors_total` | Error count | < 1% of requests |
| `ai_assistant_tool_calls_total` | Tool invocations | - |
| `ai_assistant_tokens_total` | Token usage | Within budget |
| `ai_assistant_cache_hits_total` | Cache efficiency | > 80% |

### Prometheus Setup

1. **Enable Prometheus exporter:**

```toml
[agent.observability]
metrics_enabled = true
metrics_exporter = "prometheus"
prometheus_port = 9090
```

2. **Configure Prometheus scrape:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'msft-agent'
    static_configs:
      - targets: ['msft-agent:9090']
    scrape_interval: 15s
```

3. **Kubernetes ServiceMonitor:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: msft-agent
spec:
  selector:
    matchLabels:
      app: msft-agent
  endpoints:
    - port: metrics
      interval: 15s
```

### Azure Monitor Setup

1. **Enable Azure Monitor exporter:**

```toml
[agent.observability]
metrics_enabled = true
metrics_exporter = "azure"
```

2. **Set connection string:**

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;IngestionEndpoint=https://..."
```

## Dashboards

### Grafana Dashboard

Import this dashboard JSON or create panels:

**Request Overview:**
```promql
# Request rate
rate(ai_assistant_requests_total[5m])

# Success rate
sum(rate(ai_assistant_requests_total{success="true"}[5m])) /
sum(rate(ai_assistant_requests_total[5m])) * 100

# Error rate
sum(rate(ai_assistant_errors_total[5m]))
```

**Latency:**
```promql
# P50 latency
histogram_quantile(0.5, rate(ai_assistant_request_latency_ms_bucket[5m]))

# P95 latency
histogram_quantile(0.95, rate(ai_assistant_request_latency_ms_bucket[5m]))

# P99 latency
histogram_quantile(0.99, rate(ai_assistant_request_latency_ms_bucket[5m]))
```

**Token Usage:**
```promql
# Tokens per minute
rate(ai_assistant_tokens_total[1m]) * 60

# Token breakdown
sum by (type) (rate(ai_assistant_tokens_total[5m]))
```

**Cache Performance:**
```promql
# Cache hit rate
sum(rate(ai_assistant_cache_hits_total[5m])) /
(sum(rate(ai_assistant_cache_hits_total[5m])) + sum(rate(ai_assistant_cache_misses_total[5m]))) * 100
```

### Azure Dashboard

Create an Azure Workbook with these queries:

**Request Volume:**
```kusto
requests
| where cloud_RoleName == "msft-agent"
| summarize count() by bin(timestamp, 5m)
| render timechart
```

**Error Analysis:**
```kusto
exceptions
| where cloud_RoleName == "msft-agent"
| summarize count() by type, bin(timestamp, 1h)
| render columnchart
```

**Dependency Performance:**
```kusto
dependencies
| where cloud_RoleName == "msft-agent"
| summarize avg(duration), percentile(duration, 95) by target
| order by avg_duration desc
```

## Tracing

### Jaeger Setup (Local)

1. **Start Jaeger with Docker Compose:**

```bash
docker-compose up -d jaeger
```

2. **Configure agent:**

```toml
[agent.observability]
tracing_enabled = true
tracing_exporter = "jaeger"
```

3. **Access UI:** http://localhost:16686

### Azure Application Insights

1. **Configure exporter:**

```toml
[agent.observability]
tracing_enabled = true
tracing_exporter = "azure"
```

2. **View in Azure Portal:**
   - Transaction search
   - Application map
   - Performance

### Trace Analysis

**Find slow requests:**
- Filter by duration > 5s
- Examine child spans
- Identify bottlenecks (LLM calls, tool execution)

**Debug errors:**
- Filter by status = ERROR
- Check exception details
- Review request context

## Alerting

### Prometheus Alertmanager

```yaml
# alerts.yml
groups:
  - name: msft-agent
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(ai_assistant_errors_total[5m])) /
          sum(rate(ai_assistant_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(ai_assistant_request_latency_ms_bucket[5m])) > 5000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}ms"

      - alert: LowCacheHitRate
        expr: |
          sum(rate(ai_assistant_cache_hits_total[5m])) /
          (sum(rate(ai_assistant_cache_hits_total[5m])) + sum(rate(ai_assistant_cache_misses_total[5m]))) < 0.5
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
```

### Azure Alerts

**Create alert rules:**

1. **Error Rate Alert:**
   - Condition: exceptions count > 10 in 5 minutes
   - Action: Email + PagerDuty

2. **Latency Alert:**
   - Condition: requests duration p95 > 5000ms
   - Action: Email

3. **Availability Alert:**
   - Condition: availability < 99%
   - Action: PagerDuty

## Logging

### Structured Logging

The framework uses structured JSON logging:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Request processed",
  "chat_id": "abc-123",
  "latency_ms": 1500,
  "success": true,
  "tool_calls": 2
}
```

### Log Queries

**Azure Log Analytics:**
```kusto
// Errors in last hour
traces
| where timestamp > ago(1h)
| where severityLevel >= 3
| project timestamp, message, customDimensions

// Slow requests
traces
| where customDimensions.latency_ms > 5000
| project timestamp, customDimensions.chat_id, customDimensions.latency_ms
```

**Elasticsearch:**
```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"latency_ms": {"gte": 5000}}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

## Health Monitoring

### Synthetic Monitoring

Create synthetic tests to verify availability:

```python
# synthetic_test.py
import aiohttp
import asyncio

async def health_check():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://agent.example.com/health") as response:
            data = await response.json()
            assert data["status"] == "healthy"
            assert response.status == 200

# Run every 5 minutes via scheduler
```

### Uptime Monitoring

Configure external uptime monitoring:
- Azure Application Insights Availability Tests
- Pingdom
- UptimeRobot

## Related Documentation

- [Observability Guide](../guides/observability.md) — Configuration details
- [Troubleshooting](troubleshooting.md) — Issue diagnosis
- [Production Checklist](../deployment/production-checklist.md) — Monitoring requirements
