from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderCapability(str, Enum):
    CHAT = "chat"
    ACT = "act"
    VISION = "vision"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    model: str = ""
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """A message in a conversation."""
    role: str = "user"
    content: str = ""
    images: list[bytes] | None = None


@dataclass
class ProviderResponse:
    """Response from an LLM provider."""
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: dict[str, int] | None = None
    model: str = ""
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ProviderConfig | None = None):
        self.config = config or ProviderConfig()
        self._initialized = False

    @abstractmethod
    def get_provider_name(self) -> str: ...

    @abstractmethod
    def get_capabilities(self) -> list[ProviderCapability]: ...

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    @abstractmethod
    async def chat(self, messages: list[Message]) -> ProviderResponse: ...

    async def act(
        self,
        observation: str,
        screenshot: bytes | None = None,
        previous_actions: list[dict[str, Any]] | None = None,
        task: str | None = None,
    ) -> dict[str, Any]:
        """Determine the next action based on observation. Override for structured output."""
        prompt = f"Current observation:\n{observation}\n\n"
        if task:
            prompt += f"Task: {task}\n\n"
        if previous_actions:
            prompt += "Previous actions:\n"
            for i, a in enumerate(previous_actions[-5:]):
                prompt += f"  {i}. {a.get('type', 'unknown')}: {a.get('params', {})}\n"

        prompt += "\nWhat action should be taken next? Respond with:\n"
        prompt += "ACTION: <action_type>\n"
        prompt += "PARAMS: <json params>\n"
        prompt += "REASONING: <brief explanation>\n"
        prompt += "\nIf the task is complete, respond with:\n"
        prompt += 'ACTION: finished\n'
        prompt += 'PARAMS: {}\n'
        prompt += 'REASONING: Task complete'

        messages = [Message(role="user", content=prompt)]
        if screenshot:
            messages[0].images = [screenshot]

        response = await self.chat(messages)
        return self._parse_action_response(response.content)

    def _parse_action_response(self, content: str) -> dict[str, Any]:
        """Parse a structured action response from the LLM."""
        action_type = "screenshot"
        params: dict[str, Any] = {}
        reasoning = ""

        for line in content.strip().split("\n"):
            if line.startswith("ACTION:"):
                action_type = line.split(":", 1)[1].strip().lower()
            elif line.startswith("PARAMS:"):
                params_str = line.split(":", 1)[1].strip()
                try:
                    import json
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    params = {"raw": params_str}
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        return {
            "type": action_type,
            "params": params,
            "reasoning": reasoning,
        }
