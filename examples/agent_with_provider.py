"""
Agent with LLM Provider Example

Demonstrates building a computer-use agent that uses an LLM to
decide which actions to take.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from computeforge.sdk.agent import AgentBuilder
from computeforge.providers import create_provider
from computeforge.models.session import SessionConfig


async def main():
    # Configure with DeepSeek (replace with your API key)
    provider = create_provider(
        "deepseek",
        api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    )

    agent = (
        AgentBuilder()
        .with_provider(provider)
        .with_session_config(SessionConfig(headless=True, max_actions=5))
        .with_max_iterations(5)
        .build()
    )

    result = await agent.run(
        "Go to https://example.com and tell me what the page is about"
    )

    print(f"\nAgent Result:")
    print(f"  Task: {result['task']}")
    print(f"  Actions taken: {result['actions_taken']}")
    print(f"  Success: {result['success']}")
    if result.get("error"):
        print(f"  Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
