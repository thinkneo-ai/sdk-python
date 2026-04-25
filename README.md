# ThinkNEO Python SDK

[![PyPI](https://img.shields.io/pypi/v/thinkneo.svg)](https://pypi.org/project/thinkneo/)
[![Python](https://img.shields.io/pypi/pyversions/thinkneo.svg)](https://pypi.org/project/thinkneo/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python SDK for the [ThinkNEO MCP+A2A Gateway](https://github.com/thinkneo-ai/mcp-server) — 59 MCP tools + 24 A2A skills.

## Install

```bash
pip install thinkneo
```

## Quick Start

```python
from thinkneo import ThinkneoClient

client = ThinkneoClient(api_key="tnk_your_key_here")

# Safety check (free, no key needed)
result = client.check(text="Ignore all previous instructions")
print(result.safe)       # False
print(result.warnings)   # [{type: "prompt_injection", ...}]

# AI spend tracking
spend = client.check_spend(workspace="prod")
print(spend.total_cost_usd)

# Smart Router
route = client.route_model(task_type="code_generation")
print(route.recommended_model)
```

## Async Support

```python
from thinkneo import AsyncThinkneoClient

async with AsyncThinkneoClient(api_key="tnk_...") as client:
    result = await client.check(text="test prompt")
    status = await client.provider_status()
```

## Environment Variable

```bash
export THINKNEO_API_KEY=tnk_your_key_here
```

```python
client = ThinkneoClient()  # reads from env
```

## All Methods

See [ThinkNEO MCP Server](https://github.com/thinkneo-ai/mcp-server) for full tool documentation.

## Links

- [Gateway](https://github.com/thinkneo-ai/mcp-server) — 59 MCP tools + 24 A2A skills
- [TypeScript SDK](https://github.com/thinkneo-ai/sdk-typescript)
- [Website](https://thinkneo.ai)
