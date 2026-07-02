from __future__ import annotations

from computeforge.providers.base import (
    LLMProvider,
    Message,
    ProviderCapability,
    ProviderConfig,
    ProviderResponse,
)


class OllamaProvider(LLMProvider):
    """Provider for locally-hosted Ollama models."""

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(model="llama3.2-vision", base_url="http://localhost:11434")
        super().__init__(config)

    def get_provider_name(self) -> str:
        return "ollama"

    def get_capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability.CHAT, ProviderCapability.VISION]

    async def initialize(self) -> None:
        if not self._initialized:
            try:
                import httpx
                self._client = httpx.AsyncClient(base_url=self.config.base_url, timeout=120.0)
                self._initialized = True
            except ImportError:
                raise ImportError("httpx is required")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
        self._initialized = False

    async def chat(self, messages: list[Message]) -> ProviderResponse:
        await self.initialize()
        api_messages = []
        for msg in messages:
            content = msg.content
            images: list[str] = []
            if msg.images:
                import base64
                for img in msg.images:
                    images.append(base64.b64encode(img).decode("utf-8"))
            api_messages.append({
                "role": msg.role,
                "content": content,
                "images": images if images else None,
            })

        payload = {
            "model": self.config.model,
            "messages": api_messages,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
            "stream": False,
        }

        response = await self._client.post("/api/chat", json=payload)
        data = response.json()

        return ProviderResponse(
            content=data.get("message", {}).get("content", ""),
            finish_reason="stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            model=self.config.model,
            raw=data,
        )
