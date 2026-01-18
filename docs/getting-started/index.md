# Getting Started

Welcome to the Microsoft Agent Framework! This section will help you get up and running quickly.

## Choose Your Path

### New to the Framework?

Start with the **[Quick Start Guide](quick-start.md)** — a 5-minute tutorial that will have you running your first agent.

### Setting Up for Development?

Follow the **[Installation Guide](installation.md)** for detailed setup instructions, including development dependencies and IDE configuration.

### Ready to Configure?

Check the **[Configuration Guide](configuration.md)** to learn about all configuration options and best practices.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **Azure OpenAI resource** with a deployed model (e.g., gpt-4o)
- **Azure CLI** installed and logged in (`az login`)

## Quick Overview

```bash
# 1. Clone the repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# 2. Install dependencies
pip install -e .

# 3. Configure Azure OpenAI
cp config/agent.toml.example config/agent.toml
# Edit config/agent.toml with your Azure OpenAI credentials

# 4. Run the agent
python -c "
import asyncio
from src.agent import AIAssistant

async def main():
    async with AIAssistant() as assistant:
        result = await assistant.process_question('Hello!')
        print(result.response)

asyncio.run(main())
"
```

## What's Next?

| Guide | Description |
|-------|-------------|
| [Quick Start](quick-start.md) | 5-minute tutorial |
| [Installation](installation.md) | Detailed setup |
| [Configuration](configuration.md) | Configuration options |
| [Architecture](../architecture/index.md) | How it works |
| [Tools Guide](../guides/tools.md) | Create custom tools |
