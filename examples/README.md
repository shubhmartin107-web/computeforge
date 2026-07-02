# ComputeForge Examples

This directory contains example scripts demonstrating various ComputeForge features.

## Examples

| File | Description |
|---|---|
| `basic_browser_agent.py` | Navigate a website, extract text, take screenshots |
| `workflow_composition.py` | Compose complex workflows declaratively |
| `custom_plugin.py` | Create and register a custom plugin |
| `agent_with_provider.py` | Build an agent with LLM provider integration |

## Running

```bash
# Basic example
python basic_browser_agent.py

# Workflow example
python workflow_composition.py

# Plugin example
python custom_plugin.py

# Agent with provider (set DEEPSEEK_API_KEY env var)
export DEEPSEEK_API_KEY=your_key_here
python agent_with_provider.py
```

All examples require ComputeForge to be installed (`pip install -e ..`).
