from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.providers.base import Message, ProviderConfig
from computeforge.providers.deepseek import DeepSeekProvider


class TestDeepSeekProvider:
    @pytest.fixture
    def provider(self):
        return DeepSeekProvider(config=ProviderConfig(
            api_key="test-key",
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
        ))

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "deepseek"

    def test_capabilities(self, provider):
        caps = provider.get_capabilities()
        cap_names = [c.value for c in caps]
        assert "chat" in cap_names
        assert "vision" in cap_names
        assert "tool_use" not in cap_names

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client
            await provider.initialize()
            assert provider._initialized
            mock_aoi.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.deepseek.com",
            )

    @pytest.mark.asyncio
    async def test_chat(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from DeepSeek"
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 15
            mock_usage.completion_tokens = 8

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = {"id": "deepseek-123"}

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == "Hello from DeepSeek"
            assert result.finish_reason == "stop"
            assert result.usage["prompt_tokens"] == 15
            assert result.usage["completion_tokens"] == 8
            assert result.model == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_act(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = (
                "ACTION: click\nPARAMS: {\"selector\": \"#btn\"}\nREASONING: Click the button"
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

            result = await provider.act(observation="test observation")
            assert result["type"] == "click"
            assert result["params"] == {"selector": "#btn"}
            assert result["reasoning"] == "Click the button"

    @pytest.mark.asyncio
    async def test_vision_support(self, provider):
        with patch("openai.AsyncOpenAI") as mock_aoi:
            mock_client = AsyncMock()
            mock_aoi.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = (
                "ACTION: screenshot\nPARAMS: {}\nREASONING: Taking screenshot"
            )
            mock_choice.finish_reason = "stop"

            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 20
            mock_usage.completion_tokens = 4

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = mock_usage
            mock_response.model_dump.return_value = None

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await provider.act(
                observation="test", screenshot=b"fake_image_data"
            )
            assert result["type"] == "screenshot"

    def test_parse_action_response(self, provider):
        content = (
            "ACTION: navigate\n"
            "PARAMS: {\"url\": \"https://example.com\"}\n"
            "REASONING: Go to example"
        )
        result = provider._parse_action_response(content)
        assert result["type"] == "navigate"
        assert result["params"] == {"url": "https://example.com"}
        assert result["reasoning"] == "Go to example"

    def test_parse_action_response_fallback(self, provider):
        content = "Some random response without action markers"
        result = provider._parse_action_response(content)
        assert result["type"] == "screenshot"
        assert result["params"] == {}

    def test_parse_action_response_invalid_json(self, provider):
        content = (
            "ACTION: click\n"
            "PARAMS: {bad json}\n"
            "REASONING: Clicking"
        )
        result = provider._parse_action_response(content)
        assert result["type"] == "click"
        assert result["params"] == {"raw": "{bad json}"}

    def test_parse_action_response_finished(self, provider):
        content = (
            "ACTION: finished\n"
            "PARAMS: {}\n"
            "REASONING: Task complete"
        )
        result = provider._parse_action_response(content)
        assert result["type"] == "finished"
        assert result["params"] == {}
        assert result["reasoning"] == "Task complete"

    def test_default_constructor(self):
        provider = DeepSeekProvider()
        assert provider.config.model == "deepseek-chat"
        assert provider.config.base_url == "https://api.deepseek.com"

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        provider = DeepSeekProvider(config=ProviderConfig(api_key="test"))
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
