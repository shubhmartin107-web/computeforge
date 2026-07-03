# 🔧 ComputeForge

**Open-source, extensible Computer-Use Agent Platform**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Playwright](https://img.shields.io/badge/playwright-powered-blue)](https://playwright.dev)
[![CI](https://github.com/shubhmartin107-web/computeforge/actions/workflows/ci.yml/badge.svg)](https://github.com/shubhmartin107-web/computeforge/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-937%20passing-brightgreen)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

ComputeForge is a production-oriented, open-source platform for building reliable, observable, and safe computer-use agents. It provides browser and desktop control capabilities with strong emphasis on observability, debugging, safety, and extensibility.

---

## Why ComputeForge?

Computer-use capabilities — browser automation and desktop control — are becoming essential for advanced AI agents. However, existing solutions are often:

- **Closed**: Proprietary implementations that can't be audited, extended, or self-hosted
- **Lacking observability**: Minimal insight into what the agent is doing and why
- **Weak safety controls**: Few guardrails for preventing harmful actions
- **Hard to extend**: Monolithic designs that resist customization

**ComputeForge solves these problems** by providing an open, reliable, and transparent foundation for building computer-use agents — with full observability, configurable safety, plugin-based extensibility, and first-class developer experience.

### How It Enhances Tools Like Claude Computer Use

While Claude Computer Use demonstrates the power of computer-use agents, ComputeForge adds critical production features:
- **Full session recording & visual replay** — Debug exactly what happened, step by step
- **Safety guardrails** — Permission system, risk assessment, policy enforcement
- **Plugin architecture** — Extend with custom capabilities without forking
- **Desktop control** — Beyond just browser: OS-level mouse, keyboard, screenshots
- **Multiple LLM providers** — DeepSeek, Gemini, Groq, Ollama, OpenAI
- **Self-hosted** — Full control over your data and infrastructure

### Integration Ecosystem

ComputeForge integrates with the broader AI agent ecosystem:

| System | Integration | Purpose |
|---|---|---|
| **FlowLens** | [`observability/flowlens.py`](src/computeforge/observability/flowlens.py) | Observability pipeline for agent traces |
| **GuardWeave** | [`safety/guardweave.py`](src/computeforge/safety/guardweave.py) | Governance, HITL, safety policy delegation |
| **SkillForge** | [`extensibility/skillforge.py`](src/computeforge/extensibility/skillforge.py) | Reusable skills registry and execution |
| **Memory Systems** | Via plugin hooks | Persist and retrieve session context |
| **Evaluation Platforms** | Via replay API | Score and benchmark agent performance |

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/shubhmartin107-web/computeforge.git
cd computeforge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install ComputeForge
pip install -e ".[all]"

# Install Playwright browser
playwright install chromium
```

### CLI Usage

```bash
# Navigate to a URL and explore
computeforge run https://example.com

# List capabilities
computeforge config caps

# View safety policies
computeforge config policies
```

### Python SDK

```python
import asyncio
from computeforge.sdk.client import ComputeForgeClient

async def main():
    async with ComputeForgeClient() as client:
        session = await client.create_session()
        await client.navigate("https://example.com")
        text = await client.extract_text()
        print(f"Page text: {text.data['text'][:100]}...")
        await client.screenshot()

asyncio.run(main())
```

### Agent API

```python
from computeforge.sdk.agent import AgentBuilder
from computeforge.providers import create_provider

agent = (AgentBuilder()
    .with_provider(create_provider("deepseek", api_key="..."))
    .build())

result = await agent.run("Search for ComputeForge on GitHub")
print(f"Actions taken: {result['actions_taken']}")
```

### Dashboard

```bash
# Launch the Gradio dashboard
python -m computeforge.dashboard.app
# Then open http://127.0.0.1:7860
```

### API Server

```bash
# Start the FastAPI server
uvicorn computeforge.api.server:app --host 127.0.0.1 --port 8000
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    User / Agent                       │
├──────────────────────────────────────────────────────┤
│  CLI (Typer)    SDK (Python)    Dashboard (Gradio)   │
├──────────────────────────────────────────────────────┤
│                   FastAPI REST API                    │
├──────────────────────────────────────────────────────┤
│               ComputeForge Engine                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │ Actions  │ │ Element  │ │ Session Manager  │     │
│  │ Registry │ │ Finding  │ │                  │     │
│  └────┬─────┘ └────┬─────┘ └───────┬──────────┘     │
│       │            │               │                 │
│  ┌────▼────────────▼───────────────▼──────────┐     │
│  │          Playwright / Desktop Backends      │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │ Safety & │ │ Observa- │ │ Extensibility    │     │
│  │ Permis-  │ │ bility   │ │ Plugin System    │     │
│  │ sions    │ │ Recorder │ │                  │     │
│  └────┬─────┘ └────┬─────┘ └───────┬──────────┘     │
│       │            │               │                 │
│  ┌────▼────────────▼───────────────▼──────────┐     │
│  │          Storage Layer                      │     │
│  │  SQLite (metadata) + File System (assets)   │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### Key Components

| Component | Description |
|---|---|
| **Core Engine** | Playwright-based browser automation with smart element finding |
| **Desktop Control** | PyAutoGUI + MSS backends for OS-level mouse, keyboard, screenshots |
| **Safety Layer** | Capability registry, risk assessment, policy enforcement, GuardWeave integration |
| **Observability** | Full session recording, screenshot capture, visual replay, FlowLens integration |
| **Plugin System** | Entry-point and directory-based plugin discovery, lifecycle hooks |
| **LLM Providers** | DeepSeek, OpenAI, Ollama, Groq, Gemini with uniform interface |
| **SDK** | High-level client, agent builder, workflow composition |
| **Dashboard** | Gradio-based live monitoring, replay viewer, session management, intervention |
| **CLI** | Typer-based session run, replay, config management |
| **API** | FastAPI REST API for programmatic access |

---

## Safety & Permissions

ComputeForge includes a comprehensive safety system:

```bash
# View all capabilities and their risk levels
computeforge config caps

# View default safety policies
computeforge config policies
```

The safety system:
- **Risk Assessment**: Evaluates every action before execution (URL analysis, script analysis, action type)
- **Policy Enforcement**: Configurable rules for allow/deny/require-confirmation per action type
- **Capability Registry**: Declares what the system can do with permission metadata
- **GuardWeave Integration**: Delegates policy decisions to the GuardWeave governance layer

---

## Extensibility

ComputeForge supports plugins via Python entry points:

```python
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class MyPlugin(PluginBase):
    def get_meta(self):
        return PluginMeta(name="my-plugin", version="1.0.0", description="My custom plugin")

    async def on_action_before(self, request):
        print(f"Intercepting: {request.type}")
        return request
```

Register via `pyproject.toml`:
```toml
[project.entry-points."computeforge.plugins"]
my-plugin = "my_package:MyPlugin"
```

---

## Configuration

Configuration is managed via `EngineConfig` with environment variable override (`COMPUTEFORGE_*`):

```bash
# Browser config
COMPUTEFORGE_BROWSER__HEADLESS=true
COMPUTEFORGE_BROWSER__VIEWPORT_WIDTH=1920

# Safety config
COMPUTEFORGE_SAFETY__ENABLED=true
COMPUTEFORGE_SAFETY__RISK_THRESHOLD=high

# Provider config
COMPUTEFORGE_DEFAULT_PROVIDER=deepseek
```

---

## Docker

```bash
docker compose up
```

This starts both the API server and dashboard.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

---

## Project Roadmap

- **v0.1 (current)**: Core engine, observability, safety, dashboard, CLI, SDK, providers
- **v0.2**: Desktop native backends, advanced element strategies, multi-tab sessions
- **v0.3**: Distributed execution, advanced replay, comparison views
- **v1.0**: Production hardening, comprehensive testing, CI/CD, package releases

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For security issues, see [SECURITY.md](SECURITY.md).
