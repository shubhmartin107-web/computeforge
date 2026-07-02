"""Integration tests for the ComputeEngine with a real browser.

Requires Playwright Chromium to be installed.
"""

import pytest

from computeforge.core.engine import ComputeEngine
from computeforge.models.session import SessionConfig


@pytest.mark.integration
async def test_engine_create_session(engine_config):
    engine = ComputeEngine(config=engine_config)
    session = await engine.create_session(SessionConfig(headless=True))
    assert session.id is not None
    assert session.action_count == 0


@pytest.mark.integration
async def test_engine_navigate(engine, sample_url):
    result = await engine.navigate(sample_url)
    assert result.success is True
    assert "example" in result.data.get("url", "").lower()


@pytest.mark.integration
async def test_engine_screenshot(engine):
    await engine.navigate("https://example.com")
    result = await engine.screenshot()
    assert result.success is True
    assert result.data is not None
    image = result.data.get("image")
    assert image is not None
    assert len(image) > 0


@pytest.mark.integration
async def test_engine_extract_text(engine):
    await engine.navigate("https://example.com")
    result = await engine.extract_text()
    assert result.success is True
    text = result.data.get("text", "")
    assert len(text) > 0
    assert "Example" in text or "example" in text


@pytest.mark.integration
async def test_engine_page_info(engine):
    await engine.navigate("https://example.com")
    info = await engine.get_page_info()
    assert "url" in info
    assert "title" in info
    assert info["title"] == "Example Domain"
