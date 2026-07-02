from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.core.actions import ActionType
from computeforge.core.exceptions import SafetyBlocked
from computeforge.safety.guardweave import GuardWeaveAdapter
from tests.factories import make_action_request


def test_init_with_http_url():
    adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
    assert adapter._endpoint == "http://localhost:8080"
    assert adapter._api_key is None
    assert not adapter.enabled


def test_init_without_endpoint():
    adapter = GuardWeaveAdapter()
    assert adapter._endpoint is None
    assert adapter._api_key is None
    assert not adapter.enabled


def test_init_with_api_key():
    adapter = GuardWeaveAdapter(endpoint="http://localhost:8080", api_key="sk-test")
    assert adapter._endpoint == "http://localhost:8080"
    assert adapter._api_key == "sk-test"


@pytest.mark.asyncio
async def test_connect_http():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        assert adapter.enabled
        mock_client_class.assert_called_once_with(
            base_url="http://localhost:8080",
            headers={},
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test_connect_http_with_api_key():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080", api_key="sk-test")
        await adapter.connect()
        mock_client_class.assert_called_once_with(
            base_url="http://localhost:8080",
            headers={"Authorization": "Bearer sk-test"},
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test_connect_library():
    mock_engine = MagicMock()
    mock_module = MagicMock()
    mock_module.PolicyEngine = MagicMock(return_value=mock_engine)
    with patch.dict("sys.modules", {"guardweave": mock_module}):
        adapter = GuardWeaveAdapter()
        await adapter.connect()
        assert adapter.enabled
        assert adapter._gw_engine is mock_engine


@pytest.mark.asyncio
async def test_connect_library_not_installed():
    adapter = GuardWeaveAdapter()
    await adapter.connect()
    assert not adapter.enabled
    assert not hasattr(adapter, "_gw_engine")


@pytest.mark.asyncio
async def test_assess_no_adapter():
    adapter = GuardWeaveAdapter()
    req = make_action_request()
    result = await adapter.assess(req)
    assert result["allowed"] is True
    assert result["source"] == "bypass"


@pytest.mark.asyncio
async def test_assess_http_allowed():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"allowed": True, "decision": "allow", "source": "guardweave_http"}
        ))
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        req = make_action_request()
        result = await adapter.assess(req)
        assert result["allowed"] is True
        assert result["source"] == "guardweave_http"
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_assess_http_denied():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"allowed": False, "decision": "deny", "reason": "High risk action"}
        ))
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        req = make_action_request(type=ActionType.EVALUATE, params={"script": "alert(1)"})
        result = await adapter.assess(req)
        assert result["allowed"] is False
        assert result["decision"] == "deny"
        assert result["reason"] == "High risk action"


@pytest.mark.asyncio
async def test_assess_http_error():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection error"))
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        req = make_action_request()
        result = await adapter.assess(req)
        assert result["allowed"] is True
        assert result["source"] == "fallback"


@pytest.mark.asyncio
async def test_assess_library():
    mock_engine = MagicMock()
    mock_engine.evaluate.return_value = {
        "allowed": True, "decision": "allow", "risk_score": 0.1,
    }
    mock_module = MagicMock()
    mock_module.PolicyEngine = MagicMock(return_value=mock_engine)
    with patch.dict("sys.modules", {"guardweave": mock_module}):
        adapter = GuardWeaveAdapter()
        await adapter.connect()
        req = make_action_request()
        result = await adapter.assess(req)
        assert result["allowed"] is True
        assert result["source"] == "guardweave_local"
        assert result["risk_score"] == 0.1


@pytest.mark.asyncio
async def test_assess_library_denied():
    mock_engine = MagicMock()
    mock_engine.evaluate.return_value = {
        "allowed": False, "decision": "deny", "risk_score": 0.95,
        "reason": "Policy violation",
    }
    mock_module = MagicMock()
    mock_module.PolicyEngine = MagicMock(return_value=mock_engine)
    with patch.dict("sys.modules", {"guardweave": mock_module}):
        adapter = GuardWeaveAdapter()
        await adapter.connect()
        req = make_action_request(type=ActionType.EVALUATE, params={"script": "alert(1)"})
        result = await adapter.assess(req)
        assert result["allowed"] is False
        assert result["decision"] == "deny"
        assert result["reason"] == "Policy violation"
        assert result["source"] == "guardweave_local"


@pytest.mark.asyncio
async def test_assess_library_error():
    mock_engine = MagicMock()
    mock_engine.evaluate.side_effect = Exception("eval error")
    mock_module = MagicMock()
    mock_module.PolicyEngine = MagicMock(return_value=mock_engine)
    with patch.dict("sys.modules", {"guardweave": mock_module}):
        adapter = GuardWeaveAdapter()
        await adapter.connect()
        req = make_action_request()
        result = await adapter.assess(req)
        assert result["allowed"] is True
        assert result["source"] == "fallback"


@pytest.mark.asyncio
async def test_assess_enabled_no_client_no_gw():
    adapter = GuardWeaveAdapter()
    adapter._enabled = True
    req = make_action_request()
    result = await adapter.assess(req)
    assert result["allowed"] is True
    assert result["source"] == "bypass"


@pytest.mark.asyncio
async def test_close():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        assert adapter.enabled
        await adapter.close()
        assert not adapter.enabled
        assert adapter._client is None
        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_safety_hook_allows():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"allowed": True, "decision": "allow"}
        ))
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        hook = adapter.make_safety_hook()
        req = make_action_request()
        await hook(req)


@pytest.mark.asyncio
async def test_safety_hook_blocks():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"allowed": False, "decision": "deny", "reason": "Blocked"}
        ))
        mock_client_class.return_value = mock_client
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        hook = adapter.make_safety_hook()
        req = make_action_request()
        with pytest.raises(SafetyBlocked):
            await hook(req)


@pytest.mark.asyncio
async def test_connect_http_failure():
    with patch("httpx.AsyncClient", side_effect=Exception("import failed")):
        adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
        await adapter.connect()
        assert not adapter.enabled
