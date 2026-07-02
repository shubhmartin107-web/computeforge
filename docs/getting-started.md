# Getting Started with ComputeForge

## Installation

```bash
git clone https://github.com/anomalyco/computeforge.git
cd computeforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
playwright install chromium
```

## Quick Start

### CLI

```bash
# Browse a website
computeforge run https://example.com

# View capabilities
computeforge config caps

# View policies
computeforge config policies
```

### Python SDK

```python
import asyncio
from computeforge.sdk.client import ComputeForgeClient

async def main():
    async with ComputeForgeClient() as client:
        await client.create_session()
        await client.navigate("https://example.com")
        text = await client.extract_text()
        print(text.data["text"][:200])

asyncio.run(main())
```

### Dashboard

```bash
python -m computeforge.dashboard.app
```

### API Server

```bash
uvicorn computeforge.api.server:app --host 0.0.0.0 --port 8000
```

## Next Steps

- Read the [Architecture Guide](architecture.md)
- Explore [Observability Features](observability.md)
- Learn about [Safety Controls](safety.md)
- Build with the [Extensibility System](extensibility.md)
