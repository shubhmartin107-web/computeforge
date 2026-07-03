from __future__ import annotations

from typing import Any

from computeforge.providers.base import (
    LLMProvider,
    Message,
    ProviderCapability,
    ProviderConfig,
    ProviderResponse,
)


class GroqProvider(LLMProvider):
    """Provider for Groq API (OpenAI-compatible, fast inference)."""

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
            )
        super().__init__(config)

    def get_provider_name(self) -> str:
        return "groq"

    def get_capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability.CHAT, ProviderCapability.TOOL_USE, ProviderCapability.STREAMING]

    async def initialize(self) -> None:
        if not self._initialized:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.config.api_key or "",
                    base_url=self.config.base_url,
                )
                self._initialized = True
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                ) from None

    async def chat(self, messages: list[Message]) -> ProviderResponse:
        await self.initialize()
        api_messages = []
        for m in messages:
            content: list[dict[str, Any]] = [{"type": "text", "text": m.content}]
            if m.images:
                for img in m.images:
                    if isinstance(img, str):
                        content.append({"type": "image_url", "image_url": {"url": img}})
                    elif isinstance(img, bytes):
                        import base64

                        b64 = base64.b64encode(img).decode()
                        content.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            }
                        )
            api_messages.append({"role": m.role, "content": content})

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=api_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        if not response.choices:
            return ProviderResponse(content="", finish_reason="stop", model=self.config.model)
        choice = response.choices[0]
        return ProviderResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            model=self.config.model,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )
