from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from computeforge.api.server import create_app, lifespan


@pytest.mark.asyncio
async def test_app_creation():
    app = create_app()
    assert app.title == "ComputeForge API"
    assert app.version is not None
    assert len(app.router.routes) > 0


@pytest.mark.asyncio
async def test_root_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "ComputeForge" in resp.text


@pytest.mark.asyncio
async def test_cors_headers():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://example.com"


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown():
    with (
        patch("computeforge.api.server.EngineConfig"),
        patch("computeforge.api.server.StorageBackend") as mock_storage_cls,
    ):
        mock_instance = mock_storage_cls.return_value
        mock_instance.connect = AsyncMock()
        mock_instance.close = AsyncMock()

        app = create_app()
        async with lifespan(app):
            assert app.state.storage is mock_instance
            assert app.state.config is not None

        mock_instance.connect.assert_called_once()
        mock_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_health_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == app.version
    assert "python" in data


@pytest.mark.asyncio
async def test_info_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "ComputeForge"
    assert data["version"] == app.version
    assert "endpoints" in data
