# Quick Start Guide

Get your AI agent running in 5 minutes.

## Prerequisites

- Python 3.10+
- Azure OpenAI resource with deployed model
- Azure CLI (logged in)

## Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/your-org/msft-agent-framework.git
cd msft-agent-framework

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Step 2: Configure Azure OpenAI

```bash
# Copy the example configuration
cp config/agent.toml.example config/agent.toml
```

Edit `config/agent.toml` with your Azure OpenAI details:

```toml
[agent.azure_openai]
endpoint = "https://your-resource.openai.azure.com/"
deployment = "gpt-4o"
```

Or set environment variables:

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
```

## Step 3: Login to Azure

```bash
az login
```

## Step 4: Run Your First Query

Create a file called `test_agent.py`:

```python
import asyncio
from src.agent import AIAssistant

async def main():
    async with AIAssistant() as assistant:
        # Simple question
        result = await assistant.process_question("What can you help me with?")
        print(result.response)

asyncio.run(main())
```

Run it:

```bash
python test_agent.py
```

## Step 5: Try Session Continuity

```python
import asyncio
from src.agent import AIAssistant

async def main():
    async with AIAssistant() as assistant:
        # First message - starts a new session
        result1 = await assistant.process_question("My name is Alice")
        chat_id = result1.chat_id
        print(f"Chat ID: {chat_id}")
        print(f"Response: {result1.response}\n")

        # Second message - continues the session
        result2 = await assistant.process_question(
            "What's my name?",
            chat_id=chat_id
        )
        print(f"Response: {result2.response}")

asyncio.run(main())
```

## Step 6: Use a Custom Tool

Create `src/my_tools/tools.py`:

```python
from typing import Annotated
from pydantic import Field
from src.loaders.decorators import register_tool

@register_tool(name="greet", tags=["utilities"])
def greet(
    name: Annotated[str, Field(description="Name to greet")],
) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! Welcome to the AI Assistant."
```

Add the module to your config:

```toml
# config/agent.toml
[agent.tools]
tool_modules = ["src.my_tools.tools"]
```

Test it:

```python
import asyncio
from src.agent import AIAssistant

async def main():
    async with AIAssistant() as assistant:
        result = await assistant.process_question("Please greet John")
        print(result.response)

asyncio.run(main())
```

## What's Next?

| Topic | Guide |
|-------|-------|
| Full installation options | [Installation Guide](installation.md) |
| All configuration options | [Configuration Guide](configuration.md) |
| Create more tools | [Tools Guide](../guides/tools.md) |
| Add session persistence | [Memory Guide](../guides/memory.md) |
| Deploy to production | [Deployment Guide](../deployment/index.md) |

## Need Help?

- Check the [Troubleshooting Guide](../operations/troubleshooting.md)
- Review [Architecture](../architecture/index.md) to understand how it works
- Open an issue on GitHub
