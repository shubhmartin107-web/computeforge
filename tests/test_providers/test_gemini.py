from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.providers.base import Message, ProviderConfig
from computeforge.providers.gemini import GeminiProvider


class TestGeminiProvider:
    @pytest.fixture
    def provider(self):
        return GeminiProvider(config=ProviderConfig(
            api_key="test-key",
            model="gemini-2.0-flash",
        ))

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "gemini"

    def test_capabilities(self, provider):
        caps = provider.get_capabilities()
        cap_names = [c.value for c in caps]
        assert "chat" in cap_names
        assert "vision" in cap_names
        assert "tool_use" not in cap_names

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        with patch("google.genai.aio.Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_model = MagicMock()
            mock_client.aio.models.get.return_value = mock_model

            await provider.initialize()
            assert provider._initialized
            mock_client_cls.assert_called_once_with(api_key="test-key")

    @pytest.mark.asyncio
    async def test_chat(self, provider):
        with patch("google.genai.aio.Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.aio.models.get.return_value = MagicMock()

            mock_candidate = MagicMock()
            mock_candidate.finish_reason.name = "STOP"

            mock_usage = MagicMock()
            mock_usage.prompt_token_count = 10
            mock_usage.candidates_token_count = 5

            mock_response = MagicMock()
            mock_response.text = "Hello from Gemini"
            mock_response.candidates = [mock_candidate]
            mock_response.usage_metadata = mock_usage
            mock_response.to_dict.return_value = {"text": "Hello from Gemini"}

            mock_client.models.generate_content = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == "Hello from Gemini"
            assert result.finish_reason == "STOP"
            assert result.usage["prompt_tokens"] == 10
            assert result.usage["completion_tokens"] == 5
            assert result.model == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_act(self, provider):
        with patch("google.genai.aio.Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.aio.models.get.return_value = MagicMock()

            mock_candidate = MagicMock()
            mock_candidate.finish_reason.name = "STOP"

            mock_usage = MagicMock()
            mock_usage.prompt_token_count = 8
            mock_usage.candidates_token_count = 4

            mock_response = MagicMock()
            mock_response.text = (
                "ACTION: click\n"
                "PARAMS: {\"selector\": \".btn\"}\n"
                "REASONING: Click submit button"
            )
            mock_response.candidates = [mock_candidate]
            mock_response.usage_metadata = mock_usage
            mock_response.to_dict.return_value = None

            mock_client.models.generate_content = AsyncMock(return_value=mock_response)

            result = await provider.act(observation="form visible")
            assert result["type"] == "click"
            assert result["params"] == {"selector": ".btn"}
            assert result["reasoning"] == "Click submit button"

    @pytest.mark.asyncio
    async def test_vision_support(self, provider):
        with patch("google.genai.aio.Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.aio.models.get.return_value = MagicMock()

            mock_candidate = MagicMock()
            mock_candidate.finish_reason.name = "STOP"

            mock_usage = MagicMock()
            mock_usage.prompt_token_count = 50
            mock_usage.candidates_token_count = 3

            mock_response = MagicMock()
            mock_response.text = (
                "ACTION: screenshot\nPARAMS: {}\nREASONING: Capture the current page"
            )
            mock_response.candidates = [mock_candidate]
            mock_response.usage_metadata = mock_usage
            mock_response.to_dict.return_value = None

            mock_client.models.generate_content = AsyncMock(return_value=mock_response)

            result = await provider.act(
                observation="page loaded", screenshot=b"pngdata"
            )
            assert result["type"] == "screenshot"
            assert result["reasoning"] == "Capture the current page"

    @pytest.mark.asyncio
    async def test_chat_no_candidates(self, provider):
        with patch("google.genai.aio.Client") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.aio.models.get.return_value = MagicMock()

            mock_usage = MagicMock()
            mock_usage.prompt_token_count = 0
            mock_usage.candidates_token_count = 0

            mock_response = MagicMock()
            mock_response.text = ""
            mock_response.candidates = []
            mock_response.usage_metadata = mock_usage
            mock_response.to_dict.return_value = None

            mock_client.models.generate_content = AsyncMock(return_value=mock_response)

            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == ""
            assert result.finish_reason == "stop"

    def test_default_constructor(self):
        provider = GeminiProvider()
        assert provider.config.model == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        provider = GeminiProvider(config=ProviderConfig(api_key="test"))
        provider._initialized = False
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name in ("google", "google.genai"):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="google-genai"):
                await provider.initialize()
