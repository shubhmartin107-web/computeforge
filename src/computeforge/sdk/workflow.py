from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from computeforge.core.actions import ActionResult, ActionType
from computeforge.core.engine import ComputeEngine


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str = ""
    action_type: ActionType = ActionType.SCREENSHOT
    params: dict[str, Any] = field(default_factory=dict)
    condition: Callable[[dict[str, Any]], bool] | None = None
    on_failure: str | None = None  # 'stop', 'skip', 'retry'
    max_retries: int = 1


class Workflow:
    """A composable workflow of computer-use actions."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._steps: list[WorkflowStep] = []
        self._results: list[ActionResult] = []
        self._context: dict[str, Any] = {}

    def add_step(self, step: WorkflowStep) -> Workflow:
        self._steps.append(step)
        return self

    def add_action(self, action_type: ActionType, params: dict[str, Any] | None = None, name: str = "") -> Workflow:
        self._steps.append(WorkflowStep(
            name=name or action_type.value,
            action_type=action_type,
            params=params or {},
        ))
        return self

    def navigate(self, url: str) -> Workflow:
        return self.add_action(ActionType.NAVIGATE, {"url": url}, f"Navigate to {url}")

    def click(self, selector: str) -> Workflow:
        return self.add_action(ActionType.CLICK, {"selector": selector}, f"Click {selector}")

    def type_text(self, text: str, selector: str | None = None) -> Workflow:
        return self.add_action(ActionType.TYPE, {"text": text, "selector": selector}, f"Type {text[:20]}")

    def screenshot(self, name: str = "screenshot") -> Workflow:
        return self.add_action(ActionType.SCREENSHOT, {}, name)

    def scroll(self, delta_y: int = 300) -> Workflow:
        return self.add_action(ActionType.SCROLL, {"delta_y": delta_y}, f"Scroll {delta_y}")

    def extract_text(self, name: str = "extract") -> Workflow:
        return self.add_action(ActionType.EXTRACT_TEXT, {}, name)

    @property
    def results(self) -> list[ActionResult]:
        return list(self._results)

    @property
    def context(self) -> dict[str, Any]:
        return dict(self._context)

    async def execute(self, engine: ComputeEngine) -> list[ActionResult]:
        """Execute the workflow using the given engine."""
        self._results = []
        for step in self._steps:
            for attempt in range(step.max_retries):
                try:
                    result = await engine.execute(step.action_type, **step.params)
                    self._results.append(result)
                    self._context[step.name] = result.data if result.success else None

                    if not result.success:
                        if step.on_failure == "stop":
                            return self._results
                        elif step.on_failure == "retry":
                            continue
                        elif step.on_failure == "skip":
                            break
                    break
                except Exception as e:
                    if attempt >= step.max_retries - 1:
                        result = ActionResult(success=False, action_type=step.action_type, error=str(e))
                        self._results.append(result)
                        if step.on_failure == "stop":
                            return self._results
                    else:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)  # exponential backoff

        return self._results
