from computeforge.providers.base import (
    LLMProvider,
    Message,
    ProviderCapability,
    ProviderConfig,
    ProviderResponse,
)
from computeforge.providers.deepseek import DeepSeekProvider
from computeforge.providers.gemini import GeminiProvider
from computeforge.providers.groq import GroqProvider
from computeforge.providers.ollama import OllamaProvider
from computeforge.providers.openai import OpenAIProvider

PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "groq": GroqProvider,
    "gemini": GeminiProvider,
}


def create_provider(name: str, api_key: str | None = None, model: str | None = None, base_url: str | None = None) -> LLMProvider:
    """Factory function to create a provider by name."""
    provider_cls = PROVIDER_MAP.get(name.lower())
    if provider_cls is None:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDER_MAP.keys())}")

    config = ProviderConfig(
        api_key=api_key,
        model=model or "",
        base_url=base_url,
    )
    if not config.model:
        defaults = {"deepseek": "deepseek-chat", "openai": "gpt-4o", "ollama": "llama3", "groq": "llama-3.3-70b-versatile", "gemini": "gemini-2.0-flash"}
        config.model = defaults.get(name.lower(), "")

    return provider_cls(config=config)


__all__ = [
    "DeepSeekProvider",
    "GeminiProvider",
    "GroqProvider",
    "LLMProvider",
    "Message",
    "OllamaProvider",
    "OpenAIProvider",
    "ProviderCapability",
    "ProviderConfig",
    "ProviderResponse",
    "create_provider",
]
