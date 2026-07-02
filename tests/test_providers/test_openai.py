from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.providers.base import Message, ProviderConfig
from computeforge.providers.openai import OpenAIProvider


class TestOpenAIProvider:
    @pytest.fixture
    def provider(self):
        return OpenAIProvider(config=ProviderConfig(
            api_key="test-key",
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
        ))

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "openai"

    def test_capabilities(self, provider):
        caps = provider.get_capabilities()
        cap_names = [c.value for c in caps]
        assert "chat" in cap_names
        assert "vision" in cap_names
        assert "tool_use" in cap_names
        assert "streaming" in cap_names

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client
            await provider.initialize()
            assert provider._initialized
            mock_aoi.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.openai.com/v1",
            )

    @pytest.mark.asyncio
    async def test_chat(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from OpenAI"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 12
            mock_usage.completion_tokens = 6

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "openai-123"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == "Hello from OpenAI"
            assert result.finish_reason == "stop"
            assert result.usage["prompt_tokens"] == 12
            assert result.usage["completion_tokens"] == 6
            assert result.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_act(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = (
                "ACTION: type\nPARAMS: {\"text\": \"hello\"}\nREASONING: Type greeting"
            )
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 10
            mock_usage.completion_tokens = 5

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = None

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.act(observation="type field visible")
            assert result["type"] == "type"
            assert result["params"] == {"text": "hello"}
            assert result["reasoning"] == "Type greeting"

    @pytest.mark.asyncio
    async def test_vision_support(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = (
                "ACTION: screenshot\nPARAMS: {}\nREASONING: Capture view"
            )
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 30
            mock_usage.completion_tokens = 3

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = None

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.act(
                observation="page loaded", screenshot=b"image_bytes"
            )
            assert result["type"] == "screenshot"
            assert result["reasoning"] == "Capture view"

    @pytest.mark.asyncio
    async def test_chat_with_image_message(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "I see the image"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 25
            mock_usage.completion_tokens = 5

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "openai-456"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            msg = Message(role="user", content="What is in this image?", images=[b"pngdata"])
            result = await provider.chat([msg])
            assert result.content == "I see the image"
            assert result.usage["prompt_tokens"] == 25

    def test_parse_action_response(self, provider):
        content = (
            "ACTION: scroll\nPARAMS: {\"direction\": \"down\"}\n"
            "REASONING: Scroll down to see more"
        )
        result = provider._parse_action_response(content)
        assert result["type"] == "scroll"
        assert result["params"] == {"direction": "down"}

    def test_parse_action_response_fallback(self, provider):
        result = provider._parse_action_response("no action here")
        assert result["type"] == "screenshot"
        assert result["params"] == {}
        assert result["reasoning"] == ""

    def test_default_constructor(self):
        provider = OpenAIProvider()
        assert provider.config.model == "gpt-4o"
        assert provider.config.base_url == "https://api.openai.com/v1"

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        provider = OpenAIProvider(config=ProviderConfig(api_key="test"))
        provider._initialized = False
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="pip install"):
                await provider.initialize()
