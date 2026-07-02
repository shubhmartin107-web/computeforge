from __future__ import annotations

from unittest.mock import patch

import pytest

from computeforge.providers import PROVIDER_MAP, create_provider
from computeforge.providers.base import (
    LLMProvider,
    Message,
    ProviderCapability,
    ProviderConfig,
    ProviderResponse,
)


class MinimalProvider(LLMProvider):
    def get_provider_name(self) -> str:
        return "minimal"

    def get_capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability.CHAT]

    async def chat(self, messages: list[Message]) -> ProviderResponse:
        return ProviderResponse(content="ok")


def test_provider_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        LLMProvider()


def test_provider_config_defaults():
    config = ProviderConfig()
    assert config.model == ""
    assert config.api_key is None
    assert config.base_url is None
    assert config.temperature == 0.7
    assert config.max_tokens == 4096
    assert config.top_p == 1.0
    assert config.extra_params == {}


def test_message_creation():
    msg = Message()
    assert msg.role == "user"
    assert msg.content == ""
    assert msg.images is None

    msg2 = Message(role="assistant", content="Hello", images=[b"data"])
    assert msg2.role == "assistant"
    assert msg2.content == "Hello"
    assert msg2.images == [b"data"]


def test_provider_response():
    resp = ProviderResponse()
    assert resp.content == ""
    assert resp.tool_calls is None
    assert resp.finish_reason == "stop"
    assert resp.usage is None
    assert resp.model == ""
    assert resp.raw is None

    resp2 = ProviderResponse(
        content="test",
        finish_reason="length",
        usage={"prompt_tokens": 10},
        model="gpt-4",
        raw={"id": "123"},
    )
    assert resp2.content == "test"
    assert resp2.finish_reason == "length"
    assert resp2.usage == {"prompt_tokens": 10}
    assert resp2.model == "gpt-4"
    assert resp2.raw == {"id": "123"}


def test_provider_capability_values():
    assert ProviderCapability.CHAT.value == "chat"
    assert ProviderCapability.ACT.value == "act"
    assert ProviderCapability.VISION.value == "vision"
    assert ProviderCapability.TOOL_USE.value == "tool_use"
    assert ProviderCapability.STREAMING.value == "streaming"


def test_provider_map_contains_all():
    expected = {"deepseek", "openai", "ollama", "groq", "gemini"}
    assert set(PROVIDER_MAP.keys()) == expected


def test_create_provider_valid():
    provider = create_provider("openai")
    assert provider.get_provider_name() == "openai"
    assert provider.config.model == "gpt-4o"

    provider2 = create_provider("deepseek", api_key="test-key")
    assert provider2.get_provider_name() == "deepseek"
    assert provider2.config.api_key == "test-key"
    assert provider2.config.model == "deepseek-chat"

    provider3 = create_provider("ollama", model="llama2")
    assert provider3.get_provider_name() == "ollama"
    assert provider3.config.model == "llama2"


def test_create_provider_invalid():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("nonexistent")


@pytest.mark.asyncio
async def test_base_initialize():
    provider = MinimalProvider()
    assert not provider._initialized
    await provider.initialize()
    assert provider._initialized


@pytest.mark.asyncio
async def test_base_shutdown():
    provider = MinimalProvider()
    await provider.initialize()
    await provider.shutdown()
    assert not provider._initialized


@pytest.mark.asyncio
async def test_act_with_task():
    provider = MinimalProvider()
    result = await provider.act(observation="test", task="Click the button")
    assert result["type"] == "screenshot"


@pytest.mark.asyncio
async def test_act_with_previous_actions():
    provider = MinimalProvider()
    result = await provider.act(
        observation="test",
        previous_actions=[{"type": "click", "params": {"x": 1, "y": 2}}],
    )
    assert result["type"] == "screenshot"
