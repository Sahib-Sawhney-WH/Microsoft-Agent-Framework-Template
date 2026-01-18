# Microsoft Agent Framework Documentation

Welcome to the documentation for the Microsoft Agent Framework Template — a production-ready AI agent framework with dynamic tool loading, MCP support, multi-model providers, and enterprise features.

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Get started quickly | [Quick Start Guide](getting-started/quick-start.md) |
| Understand the architecture | [Architecture Overview](architecture/index.md) |
| Deploy to production | [Deployment Guide](deployment/index.md) |
| Create custom tools | [Tools Guide](guides/tools.md) |
| Configure security | [Security Guide](guides/security.md) |
| Set up monitoring | [Monitoring Guide](operations/monitoring.md) |

## Features

- **Dynamic Tool Loading** — Hybrid decorator + JSON tool discovery
- **Multi-Model Support** — Azure OpenAI, OpenAI, Anthropic, and custom providers
- **MCP Integration** — Connect to external MCP servers (stdio, HTTP, WebSocket)
- **Multi-Agent Workflows** — Sequential and graph-based agent pipelines
- **Session Management** — Redis cache + blob persistence with auto-summarization
- **Observability** — OpenTelemetry tracing and metrics
- **Security** — Rate limiting, input validation, prompt injection detection
- **Health Checks** — Kubernetes-ready readiness/liveness probes

## Documentation Structure

### Getting Started
New to the framework? Start here.

- [Quick Start](getting-started/quick-start.md) — 5-minute guide to running your first agent
- [Installation](getting-started/installation.md) — Detailed installation instructions
- [Configuration](getting-started/configuration.md) — Configure your agent

### Architecture
Understand how the framework works.

- [Architecture Overview](architecture/index.md) — System diagrams, component overview, request flow

### Guides
Learn how to use specific features.

- [Tools Guide](guides/tools.md) — Create and configure tools
- [Memory Guide](guides/memory.md) — Session management and persistence
- [Security Guide](guides/security.md) — Rate limiting, input validation
- [Observability Guide](guides/observability.md) — Tracing and metrics
- [Workflows Guide](guides/workflows.md) — Multi-agent workflows
- [MCP Integration](guides/mcp-integration.md) — Connect to MCP servers

### Deployment
Deploy your agent to production.

- [Deployment Overview](deployment/index.md) — Comparison of deployment options
- [Local Development](deployment/local-development.md) — Set up local dev environment
- [Docker](deployment/docker.md) — Build and run containers
- [Kubernetes](deployment/kubernetes.md) — Deploy to Kubernetes
- [Azure Container Apps](deployment/azure-container-apps.md) — Serverless deployment
- [Azure Setup](deployment/azure-setup.md) — Configure Azure resources
- [Production Checklist](deployment/production-checklist.md) — Pre-production verification

### Operations
Run and maintain your agent in production.

- [Operations Overview](operations/index.md) — Day-to-day operations
- [Monitoring](operations/monitoring.md) — Dashboards and alerts
- [Troubleshooting](operations/troubleshooting.md) — Common issues and solutions
- [Scaling](operations/scaling.md) — Handle increased load

### Reference
Detailed technical reference.

- [Configuration Reference](reference/configuration-reference.md) — All configuration options
- [Environment Variables](reference/environment-variables.md) — Environment variable reference

### Contributing
Help improve the framework.

- [Contributing Guide](contributing/index.md) — How to contribute
- [Development Setup](contributing/development-setup.md) — Set up your dev environment

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| Memory | 512 MB | 2+ GB |
| Azure OpenAI | Required | Required |
| Redis | Optional | Recommended |

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/msft-agent-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/msft-agent-framework/discussions)

## License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
