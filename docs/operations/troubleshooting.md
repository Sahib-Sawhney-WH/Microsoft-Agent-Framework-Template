# Troubleshooting Guide

Common issues and solutions for the Microsoft Agent Framework.

## Quick Diagnosis

### Health Check

```bash
# Check service health
curl http://localhost:8080/health

# Check specific components
curl http://localhost:8080/health | jq '.components'
```

### Log Analysis

```bash
# Recent errors
kubectl logs -l app=msft-agent -n msft-agent --tail=100 | grep ERROR

# Rate limit events
kubectl logs -l app=msft-agent -n msft-agent | grep "RateLimitExceeded"
```

---

## Authentication Issues

### Azure DefaultAzureCredential Failed

**Symptom:**
```
DefaultAzureCredential failed to retrieve a token from the included credentials
```

**Solutions:**

1. **Local development:**
   ```bash
   az login
   az account set --subscription "Your Subscription"
   ```

2. **Service Principal:**
   ```bash
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   ```

3. **Managed Identity (in Azure):**
   - Verify managed identity is enabled
   - Check RBAC role assignments

### Redis Authentication Failed

**Symptom:**
```
NOAUTH Authentication required
```

**Cause:** Data Access Policy not configured

**Solution:**
```bash
# Create Data Access Policy
az redis access-policy-assignment create \
  --name "your-policy" \
  --policy-name "Data Owner" \
  --object-id "$YOUR_OID" \
  --redis-cache-name your-redis \
  --resource-group your-rg
```

See [Azure Setup](../deployment/azure-setup.md) for details.

### Storage Permission Denied

**Symptom:**
```
AuthorizationPermissionMismatch
```

**Solution:**
```bash
# Assign Storage Blob Data Contributor
az role assignment create \
  --assignee "$YOUR_OID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/.../storageAccounts/youraccount"
```

**Note:** RBAC propagation can take 5-15 minutes.

---

## Connection Issues

### Redis Connection Refused

**Symptom:**
```
Connection refused (localhost:6379)
```

**Solutions:**

1. **Check Redis is running:**
   ```bash
   docker ps | grep redis
   ```

2. **Start Redis:**
   ```bash
   docker-compose up -d redis
   ```

3. **Verify configuration:**
   ```toml
   [agent.memory.cache]
   host = "localhost"  # or correct hostname
   port = 6379         # or 6380 for SSL
   ssl = false         # true for Azure Redis
   ```

### Azure OpenAI Connection Failed

**Symptom:**
```
openai.error.APIConnectionError
```

**Solutions:**

1. **Check endpoint URL:**
   ```bash
   curl https://your-resource.openai.azure.com/
   ```

2. **Verify deployment exists:**
   ```bash
   az cognitiveservices account deployment list \
     --name your-openai \
     --resource-group your-rg
   ```

3. **Check RBAC:**
   ```bash
   az role assignment list --assignee $YOUR_OID | grep "Cognitive Services"
   ```

### MCP Server Not Responding

**Symptom:**
```
MCP server connection timeout
```

**Solutions:**

1. **For stdio servers:**
   ```bash
   # Test the command directly
   uvx mcp-server-calculator
   ```

2. **For HTTP servers:**
   ```bash
   curl -v https://your-mcp-server/health
   ```

3. **Check configuration:**
   ```toml
   [[agent.mcp]]
   name = "calculator"
   enabled = true  # Ensure enabled
   command = "uvx"
   args = ["mcp-server-calculator"]
   ```

---

## Performance Issues

### High Latency

**Diagnosis:**
```python
# Check latency breakdown in traces
# Look at span durations for:
# - llm_call (LLM response time)
# - tool_execution (tool overhead)
# - cache_operation (Redis latency)
```

**Solutions:**

1. **LLM latency:**
   - Check Azure OpenAI quota/throttling
   - Consider using a faster model (gpt-4o-mini)
   - Enable caching for repeated queries

2. **Cache latency:**
   - Use closer Redis region
   - Check Redis tier (upgrade if needed)

3. **Network latency:**
   - Deploy in same region as Azure services
   - Use private endpoints

### Memory Issues

**Symptom:**
```
Container OOMKilled
```

**Solutions:**

1. **Increase memory limits:**
   ```yaml
   resources:
     limits:
       memory: "4Gi"
   ```

2. **Enable summarization:**
   ```toml
   [agent.memory.summarization]
   enabled = true
   max_tokens = 8000
   ```

3. **Check for memory leaks:**
   ```bash
   kubectl top pods -n msft-agent
   ```

### High Error Rate

**Diagnosis:**
```bash
# Check error types
kubectl logs -l app=msft-agent | grep ERROR | cut -d' ' -f5 | sort | uniq -c
```

**Common causes:**
- Rate limiting (check quotas)
- Input validation failures (check blocked patterns)
- Tool execution errors (check tool logs)

---

## Configuration Issues

### Module Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
pip install -e .
# or
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Configuration Not Loading

**Diagnosis:**
```python
from src.config import load_config
config = load_config()
print(config.azure_openai.endpoint)
```

**Solutions:**

1. **Check file exists:**
   ```bash
   ls config/agent.toml
   ```

2. **Validate TOML syntax:**
   ```bash
   python -c "import tomli; tomli.loads(open('config/agent.toml').read())"
   ```

3. **Check environment overrides:**
   ```bash
   env | grep AZURE
   ```

### Tool Not Discovered

**Symptom:** Tool available in code but not shown by agent

**Solutions:**

1. **Check module is listed:**
   ```toml
   [agent.tools]
   tool_modules = ["src.my_tools.tools"]
   ```

2. **Verify decorator:**
   ```python
   @register_tool(name="my_tool", enabled=True)  # enabled must be True
   ```

3. **Import test:**
   ```python
   from src.my_tools.tools import my_tool
   from src.loaders.decorators import get_registered_tools
   print(get_registered_tools())
   ```

---

## Kubernetes Issues

### Pod Not Starting

**Diagnosis:**
```bash
kubectl describe pod -l app=msft-agent -n msft-agent
kubectl get events -n msft-agent --sort-by='.lastTimestamp'
```

**Common causes:**

1. **ImagePullBackOff:**
   ```bash
   # Check image exists
   az acr repository show-tags --name myregistry --repository msft-agent

   # Check pull secret
   kubectl get secret acr-secret -n msft-agent
   ```

2. **CrashLoopBackOff:**
   ```bash
   # Check previous logs
   kubectl logs -l app=msft-agent -n msft-agent --previous
   ```

3. **Pending (resources):**
   ```bash
   kubectl describe nodes | grep -A 5 "Allocated resources"
   ```

### Health Check Failing

**Diagnosis:**
```bash
kubectl exec -it deploy/msft-agent -n msft-agent -- curl localhost:8080/health
```

**Solutions:**

1. **Increase startup time:**
   ```yaml
   startupProbe:
     failureThreshold: 30  # More retries
     periodSeconds: 10
   ```

2. **Check application logs:**
   ```bash
   kubectl logs -l app=msft-agent -n msft-agent --tail=50
   ```

---

## Security Issues

### Rate Limit Exceeded

**Symptom:**
```
RateLimitExceeded: 60/60 requests per minute
```

**Solutions:**

1. **Increase limits (if appropriate):**
   ```toml
   [agent.security.rate_limit]
   requests_per_minute = 120
   ```

2. **Check for abuse:**
   ```bash
   # Find high-volume users
   grep "rate_limit" logs.txt | cut -d'user=' -f2 | sort | uniq -c | sort -rn
   ```

### Prompt Injection Blocked

**Symptom:**
```
ValidationError: Input contains potentially harmful content
```

**Solutions:**

1. **Review blocked patterns:**
   ```python
   from src.security import detect_prompt_injection
   print(detect_prompt_injection("your input"))
   ```

2. **Check for false positives:**
   - Review blocked inputs in logs
   - Adjust patterns if needed

---

## Getting Help

### Collect Diagnostic Info

```bash
# System info
kubectl version
python --version
pip list | grep -E "azure|openai|agent"

# Configuration (sanitized)
cat config/agent.toml | grep -v "secret\|password\|key"

# Recent logs
kubectl logs -l app=msft-agent -n msft-agent --tail=200 > debug.log

# Health status
curl http://localhost:8080/health > health.json
```

### Support Channels

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** Check guides for configuration details
- **Logs:** Review detailed error messages

## Related Documentation

- [Monitoring Guide](monitoring.md) — Set up monitoring
- [Operations Overview](index.md) — Day-to-day operations
- [Production Checklist](../deployment/production-checklist.md) — Verify configuration
