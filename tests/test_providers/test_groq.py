from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.providers.base import Message, ProviderConfig
from computeforge.providers.groq import GroqProvider


class TestGroqProvider:
    @pytest.fixture
    def provider(self):
        return GroqProvider(config=ProviderConfig(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        ))

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "groq"

    def test_capabilities(self, provider):
        caps = provider.get_capabilities()
        cap_names = [c.value for c in caps]
        assert "chat" in cap_names
        assert "tool_use" in cap_names
        assert "streaming" in cap_names
        assert "vision" not in cap_names

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client
            await provider.initialize()
            assert provider._initialized
            mock_aoi.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.groq.com/openai/v1",
            )

    @pytest.mark.asyncio
    async def test_chat(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from Groq"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 15
            mock_usage.completion_tokens = 10

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "groq-123"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == "Hello from Groq"
            assert result.finish_reason == "stop"
            assert result.usage["prompt_tokens"] == 15
            assert result.usage["completion_tokens"] == 10
            assert result.model == "llama-3.3-70b-versatile"

    @pytest.mark.asyncio
    async def test_act(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = (
                "ACTION: navigate\n"
                "PARAMS: {\"url\": \"https://example.com\"}\n"
                "REASONING: Navigate to example"
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

            result = await provider.act(observation="at homepage")
            assert result["type"] == "navigate"
            assert result["params"] == {"url": "https://example.com"}

    @pytest.mark.asyncio
    async def test_chat_with_image_bytes(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "I see the image content"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 25
            mock_usage.completion_tokens = 5

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "groq-456"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            msg = Message(role="user", content="What is in this image?", images=[b"pngdata"])
            result = await provider.chat([msg])
            assert result.content == "I see the image content"

    @pytest.mark.asyncio
    async def test_chat_empty_choices(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = []
            mock_response.model_dump.return_value = None

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == ""
            assert result.finish_reason == "stop"
            assert result.model == "llama-3.3-70b-versatile"

    def test_parse_action_response(self, provider):
        content = (
            "ACTION: finished\nPARAMS: {}\nREASONING: Task is complete"
        )
        result = provider._parse_action_response(content)
        assert result["type"] == "finished"
        assert result["reasoning"] == "Task is complete"

    def test_default_constructor(self):
        provider = GroqProvider()
        assert provider.config.model == "llama-3.3-70b-versatile"
        assert provider.config.base_url == "https://api.groq.com/openai/v1"

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        provider = GroqProvider(config=ProviderConfig(api_key="test"))
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

    @pytest.mark.asyncio
    async def test_chat_with_image_string(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "I see the image URL"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 25
            mock_usage.completion_tokens = 5

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "groq-str-img"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            msg = Message(
                role="user",
                content="What is in this image?",
                images=["https://example.com/image.png"],
            )
            result = await provider.chat([msg])
            assert result.content == "I see the image URL"
            assert result.usage["prompt_tokens"] == 25
