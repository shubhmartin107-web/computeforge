from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from computeforge.core.actions import ActionType
from computeforge.core.engine import ComputeEngine
from computeforge.models.config import EngineConfig
from computeforge.models.session import SessionConfig
from computeforge.providers.base import LLMProvider

logger = logging.getLogger("computeforge.sdk.agent")


class AgentBuilder:
    """Build a computer-use agent by composing a provider and the engine.

    Example:
        agent = (AgentBuilder()
            .with_provider(DeepSeekProvider(config))
            .with_config(EngineConfig())
            .build())
        result = await agent.run("Search for Python tutorials")
    """

    def __init__(self):
        self._provider: LLMProvider | None = None
        self._config: EngineConfig | None = None
        self._session_config: SessionConfig | None = None
        self._pre_action_hooks: list[Callable] = []
        self._post_action_hooks: list[Callable] = []
        self._max_iterations: int = 20

    def with_provider(self, provider: LLMProvider) -> AgentBuilder:
        self._provider = provider
        return self

    def with_config(self, config: EngineConfig) -> AgentBuilder:
        self._config = config
        return self

    def with_session_config(self, config: SessionConfig) -> AgentBuilder:
        self._session_config = config
        return self

    def with_max_iterations(self, n: int) -> AgentBuilder:
        self._max_iterations = n
        return self

    def add_pre_action_hook(self, hook: Callable) -> AgentBuilder:
        self._pre_action_hooks.append(hook)
        return self

    def add_post_action_hook(self, hook: Callable) -> AgentBuilder:
        self._post_action_hooks.append(hook)
        return self

    def build(self) -> Agent:
        if self._provider is None:
            raise ValueError("Provider is required. Call with_provider() first.")

        engine = ComputeEngine(config=self._config or EngineConfig())
        for hook in self._pre_action_hooks:
            engine.register_pre_action_hook(hook)
        for hook in self._post_action_hooks:
            engine.register_post_action_hook(hook)

        return Agent(
            provider=self._provider,
            engine=engine,
            session_config=self._session_config or SessionConfig(),
            max_iterations=self._max_iterations,
        )


class Agent:
    """A computer-use agent that uses an LLM to decide actions."""

    def __init__(
        self,
        provider: LLMProvider,
        engine: ComputeEngine,
        session_config: SessionConfig,
        max_iterations: int = 20,
    ):
        self._provider = provider
        self._engine = engine
        self._session_config = session_config
        self._max_iterations = max_iterations
        self._action_history: list[dict[str, Any]] = []

    @property
    def action_history(self) -> list[dict[str, Any]]:
        return list(self._action_history)

    @property
    def engine(self) -> ComputeEngine:
        return self._engine

    async def run(self, task: str) -> dict[str, Any]:
        """Run the agent on a task. Returns summary of results."""
        await self._engine.create_session(self._session_config)
        await self._engine.start_session()

        summary: dict[str, Any] = {
            "task": task,
            "actions_taken": 0,
            "success": False,
            "error": None,
        }

        try:
            for _iteration in range(self._max_iterations):
                if not self._engine.is_running:
                    break

                # Get current state
                screenshot_result = await self._engine.screenshot()
                screenshot_bytes = (
                    screenshot_result.data.get("image") if screenshot_result.success else None
                )
                text_result = await self._engine.extract_text()
                page_text = text_result.data.get("text", "") if text_result.success else ""

                # Ask provider for next action
                action = await self._provider.act(
                    observation=page_text[:2000],
                    screenshot=screenshot_bytes,
                    previous_actions=self._action_history[-5:],
                    task=task,
                )

                atype_str = action.get("type", "screenshot")
                params = action.get("params", {})

                # Check for termination
                if atype_str == "finished" or atype_str == "done":
                    summary["success"] = True
                    break

                # Execute the action
                try:
                    atype = ActionType(atype_str)
                    result = await self._engine.execute(atype, **params)

                    self._action_history.append(
                        {
                            "type": atype_str,
                            "params": params,
                            "success": result.success,
                            "duration_ms": result.duration_ms,
                        }
                    )
                    summary["actions_taken"] += 1

                except Exception as e:
                    self._action_history.append(
                        {
                            "type": atype_str,
                            "params": params,
                            "success": False,
                            "error": str(e),
                        }
                    )
                    summary["actions_taken"] += 1

            if summary["actions_taken"] >= self._max_iterations:
                summary["success"] = True
                summary["note"] = "Reached max iterations"

        except Exception as e:
            summary["error"] = str(e)
            logger.error(f"Agent run failed: {e}")

        finally:
            await self._engine.stop_session()

        return summary
