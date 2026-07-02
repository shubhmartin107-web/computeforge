from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.providers.base import Message, ProviderConfig
from computeforge.providers.ollama import OllamaProvider


class TestOllamaProvider:
    @pytest.fixture
    def provider(self):
        return OllamaProvider(config=ProviderConfig(
            model="llama3.2-vision",
            base_url="http://localhost:11434",
        ))

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "ollama"

    def test_capabilities(self, provider):
        caps = provider.get_capabilities()
        cap_names = [c.value for c in caps]
        assert "chat" in cap_names
        assert "vision" in cap_names
        assert "streaming" not in cap_names

    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client
            await provider.initialize()
            assert provider._initialized
            mock_httpx.assert_called_once_with(
                base_url="http://localhost:11434",
                timeout=120.0,
            )

    @pytest.mark.asyncio
    async def test_chat(self, provider):
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {"content": "Hello from Ollama"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            }
            mock_client.post = AsyncMock(return_value=mock_response)

            await provider.initialize()
            result = await provider.chat([Message(role="user", content="Hi")])
            assert result.content == "Hello from Ollama"
            assert result.finish_reason == "stop"
            assert result.usage["prompt_tokens"] == 10
            assert result.usage["completion_tokens"] == 5
            assert result.model == "llama3.2-vision"

    @pytest.mark.asyncio
    async def test_act(self, provider):
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {
                    "content": (
                        "ACTION: click\n"
                        "PARAMS: {\"selector\": \"#btn\"}\n"
                        "REASONING: Click the button"
                    )
                },
                "prompt_eval_count": 8,
                "eval_count": 4,
            }
            mock_client.post = AsyncMock(return_value=mock_response)

            await provider.initialize()
            result = await provider.act(observation="button visible")
            assert result["type"] == "click"
            assert result["params"] == {"selector": "#btn"}
            assert result["reasoning"] == "Click the button"

    @pytest.mark.asyncio
    async def test_vision_support(self, provider):
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {
                    "content": (
                        "ACTION: screenshot\n"
                        "PARAMS: {}\n"
                        "REASONING: Capture current view"
                    )
                },
                "prompt_eval_count": 20,
                "eval_count": 2,
            }
            mock_client.post = AsyncMock(return_value=mock_response)

            await provider.initialize()
            result = await provider.act(
                observation="page loaded", screenshot=b"image_data"
            )
            assert result["type"] == "screenshot"

    @pytest.mark.asyncio
    async def test_shutdown(self, provider):
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client
            await provider.initialize()
            assert provider._initialized

            await provider.shutdown()
            assert not provider._initialized
            mock_client.aclose.assert_called_once()

    def test_default_constructor(self):
        provider = OllamaProvider()
        assert provider.config.model == "llama3.2-vision"
        assert provider.config.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_initialize_import_error(self):
        provider = OllamaProvider(config=ProviderConfig(api_key="test"))
        provider._initialized = False
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="httpx"):
                await provider.initialize()
