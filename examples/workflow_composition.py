"""
Workflow Composition Example

Demonstrates composing complex computer-use workflows using the
Workflow class with declarative step definitions.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from computeforge.core.engine import ComputeEngine
from computeforge.sdk.workflow import Workflow
from computeforge.models.config import EngineConfig
from computeforge.models.session import SessionConfig


async def main():
    config = EngineConfig()
    config.browser.headless = True

    engine = ComputeEngine(config=config)
    await engine.create_session(SessionConfig(headless=True))
    await engine.start_session()

    # Build a workflow
    workflow = (
        Workflow("demo")
        .navigate("https://example.com")
        .screenshot("homepage")
        .extract_text("content")
        .scroll(delta_y=500)
        .screenshot("scrolled")
    )

    print(f"Executing workflow: {workflow.name}")
    print(f"Steps: {len(workflow._steps)}")

    results = await workflow.execute(engine)

    for i, result in enumerate(results):
        icon = "✅" if result.success else "❌"
        print(f"  {icon} Step {i}: {result.action_type} ({result.duration_ms:.0f}ms)")

    await engine.stop_session()
    print(f"\nWorkflow complete: {len(results)} actions")


if __name__ == "__main__":
    asyncio.run(main())
