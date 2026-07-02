from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.core.exceptions import PluginError
from computeforge.extensibility.skillforge import SkillForgeAdapter


@pytest.mark.asyncio
async def test_init_with_http_url():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    assert adapter._endpoint == "http://localhost:8080"
    assert adapter._local is False
    assert adapter._enabled is False
    assert adapter._client is None


@pytest.mark.asyncio
async def test_init_with_local_library():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    assert adapter._endpoint is None
    assert adapter._local is True
    assert adapter._enabled is False


@pytest.mark.asyncio
async def test_connect_http_success():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        await adapter.connect()
        assert adapter._enabled is True
        assert adapter._client is not None


@pytest.mark.asyncio
async def test_connect_local_success():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    with patch.dict("sys.modules", {"skillforge": MagicMock()}):
        await adapter.connect()
        assert adapter._enabled is True
        assert adapter._skillforge_available is True


@pytest.mark.asyncio
async def test_execute_skill_http_mode():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "result": "done"}
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        result = await adapter.execute_skill("test_skill", {"param1": "val1"})
        assert result == {"success": True, "result": "done"}
        mock_client.post.assert_called_once_with(
            "/api/v1/skills/test_skill/execute",
            json={"params": {"param1": "val1"}},
        )


@pytest.mark.asyncio
async def test_execute_skill_local_mode():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skill = MagicMock()
    mock_skill.name = "test_skill"
    mock_skill.description = "A test skill"
    mock_skill.version = "1.0.0"
    mock_skill.execute.return_value = "local_result"

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_skill

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry
    mock_skillforge.SkillContext = MagicMock

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        result = await adapter.execute_skill("test_skill", {"key": "val"})
        assert result["success"] is True
        assert result["result"] == "local_result"
        assert result["skill"] == "test_skill"


@pytest.mark.asyncio
async def test_execute_skill_not_connected():
    adapter = SkillForgeAdapter(endpoint=None, local=False)
    with pytest.raises(PluginError, match="SkillForge not connected"):
        await adapter.execute_skill("test_skill", {})


@pytest.mark.asyncio
async def test_list_skills_http_mode():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "skills": [
                {"name": "skill1", "description": "desc1", "version": "1.0"},
                {"name": "skill2", "description": "desc2", "version": "2.0"},
            ]
        }
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        skills = await adapter.list_skills()
        assert len(skills) == 2
        assert skills[0]["name"] == "skill1"
        assert skills[1]["name"] == "skill2"


@pytest.mark.asyncio
async def test_list_skills_local_mode():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skill1 = MagicMock()
    mock_skill1.name = "local_skill1"
    mock_skill1.description = "local desc 1"
    mock_skill1.version = "0.1.0"
    mock_skill2 = MagicMock()
    mock_skill2.name = "local_skill2"
    mock_skill2.description = "local desc 2"
    mock_skill2.version = "0.2.0"

    mock_registry = MagicMock()
    mock_registry.list.return_value = [mock_skill1, mock_skill2]

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        skills = await adapter.list_skills()
        assert len(skills) == 2
        assert skills[0]["name"] == "local_skill1"
        assert skills[1]["name"] == "local_skill2"


@pytest.mark.asyncio
async def test_execute_skill_http_error():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        with pytest.raises(PluginError, match="SkillForge execute request failed"):
            await adapter.execute_skill("test_skill", {})


@pytest.mark.asyncio
async def test_close():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        assert adapter._enabled is True
        await adapter.close()
        assert adapter._enabled is False
        assert adapter._client is None
        mock_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_skills_not_connected():
    adapter = SkillForgeAdapter(endpoint=None, local=False)
    skills = await adapter.list_skills()
    assert skills == []


@pytest.mark.asyncio
async def test_enabled_property():
    adapter = SkillForgeAdapter()
    assert adapter.enabled is False
    adapter._enabled = True
    assert adapter.enabled is True


@pytest.mark.asyncio
async def test_connect_http_failure():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.side_effect = Exception("Connection failed")
        await adapter.connect()
        assert adapter._enabled is False
        assert adapter._client is None


@pytest.mark.asyncio
async def test_connect_local_not_installed():
    import builtins
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "skillforge":
            raise ImportError("No module named skillforge")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=mock_import):
        await adapter.connect()
        assert adapter._enabled is False
        assert adapter._skillforge_available is False


@pytest.mark.asyncio
async def test_list_skills_http_failure():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Request failed"))
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        skills = await adapter.list_skills()
        assert skills == []


@pytest.mark.asyncio
async def test_list_skills_local_failure():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry = MagicMock(side_effect=Exception("registry error"))

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        skills = await adapter.list_skills()
        assert skills == []


@pytest.mark.asyncio
async def test_list_skills_no_available_backend():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    adapter._enabled = True
    skills = await adapter.list_skills()
    assert skills == []


@pytest.mark.asyncio
async def test_execute_skill_local_not_found():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_registry = MagicMock()
    mock_registry.get.return_value = None

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry
    mock_skillforge.SkillContext = MagicMock

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        with pytest.raises(PluginError, match="not found in local SkillForge"):
            await adapter.execute_skill("unknown", {})


@pytest.mark.asyncio
async def test_execute_skill_local_plugin_error():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skill = MagicMock()
    mock_skill.execute.side_effect = PluginError("custom plugin error")

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_skill

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry
    mock_skillforge.SkillContext = MagicMock

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        with pytest.raises(PluginError, match="custom plugin error"):
            await adapter.execute_skill("test_skill", {})


@pytest.mark.asyncio
async def test_execute_skill_local_unexpected_error():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skill = MagicMock()
    mock_skill.execute.side_effect = ValueError("unexpected")

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_skill

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry
    mock_skillforge.SkillContext = MagicMock

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        with pytest.raises(PluginError, match="Local SkillForge execution failed"):
            await adapter.execute_skill("test_skill", {})


@pytest.mark.asyncio
async def test_execute_skill_not_available():
    adapter = SkillForgeAdapter(endpoint=None, local=False)
    adapter._enabled = True
    with pytest.raises(PluginError, match="SkillForge not available"):
        await adapter.execute_skill("test_skill", {})


@pytest.mark.asyncio
async def test_get_skill_http_mode():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "test", "description": "desc", "version": "1.0"}
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        result = await adapter.get_skill("test")
        assert result == {"name": "test", "description": "desc", "version": "1.0"}


@pytest.mark.asyncio
async def test_get_skill_http_error():
    adapter = SkillForgeAdapter(endpoint="http://localhost:8080", local=False)
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("fail"))
        mock_client_cls.return_value = mock_client
        await adapter.connect()
        result = await adapter.get_skill("test")
        assert result is None


@pytest.mark.asyncio
async def test_get_skill_local_mode():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skill = MagicMock()
    mock_skill.name = "local_skill"
    mock_skill.description = "local desc"
    mock_skill.version = "0.1.0"

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_skill

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        result = await adapter.get_skill("local_skill")
        assert result == {"name": "local_skill", "description": "local desc", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_get_skill_local_not_found():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_registry = MagicMock()
    mock_registry.get.return_value = None

    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry.return_value = mock_registry

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        result = await adapter.get_skill("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_get_skill_local_error():
    adapter = SkillForgeAdapter(endpoint=None, local=True)
    mock_skillforge = MagicMock()
    mock_skillforge.SkillRegistry = MagicMock(side_effect=Exception("registry error"))

    with patch.dict("sys.modules", {"skillforge": mock_skillforge}):
        await adapter.connect()
        result = await adapter.get_skill("test")
        assert result is None


@pytest.mark.asyncio
async def test_get_skill_not_available():
    adapter = SkillForgeAdapter(endpoint=None, local=False)
    result = await adapter.get_skill("test")
    assert result is None
