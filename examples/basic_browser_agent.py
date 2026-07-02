"""
Basic Browser Agent Example

Demonstrates using the ComputeForge SDK to navigate a website,
interact with elements, and extract information.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from computeforge.sdk.client import ComputeForgeClient
from computeforge.core.actions import ActionType


async def main():
    async with ComputeForgeClient() as client:
        session = await client.create_session()
        print(f"Session created: {session.id[:8]}...")

        # Navigate
        result = await client.navigate("https://example.com")
        print(f"Navigated: {result.data}")

        # Extract text
        result = await client.extract_text()
        if result.success:
            text = result.data.get("text", "")
            print(f"Page text ({len(text)} chars): {text[:200]}...")

        # Take screenshot
        result = await client.screenshot()
        if result.success:
            print(f"Screenshot: {len(result.data.get('image', b''))} bytes")

        # Scroll
        result = await client.scroll(delta_y=300)
        print(f"Scrolled: {result.success}")

        print(f"\nSession complete: {session.action_count} actions")


if __name__ == "__main__":
    asyncio.run(main())
