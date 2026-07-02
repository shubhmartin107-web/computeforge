from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.core.actions import ActionRequest, ActionType
from computeforge.core.browser import BrowserManager, BrowserType
from computeforge.core.exceptions import ActionFailed, BrowserError, ElementNotFound
from tests.mocks.playwright_mock import MockPlaywright


@pytest.fixture
def browser():
    b = BrowserManager(headless=True)
    return b


@pytest.mark.asyncio
async def test_browser_type_values():
    assert BrowserType.CHROMIUM.value == "chromium"
    assert BrowserType.FIREFOX.value == "firefox"
    assert BrowserType.WEBKIT.value == "webkit"


@pytest.mark.asyncio
async def test_start_stop():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        assert b.is_running
        assert b.browser_type_name == "chromium"
        assert b.metrics["pages_loaded"] == 0
        await b.stop()
        assert not b.is_running


@pytest.mark.asyncio
async def test_start_retry_then_fail():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(side_effect=Exception("Launch failed"))
        with pytest.raises(BrowserError, match="Failed to start browser after 3 attempts"):
            await b.start()


@pytest.mark.asyncio
async def test_restart():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        await b.restart()
        assert b.is_running


@pytest.mark.asyncio
async def test_page_property_raises_when_not_started():
    b = BrowserManager(headless=True)
    with pytest.raises(BrowserError, match="Browser not started"):
        _ = b.page


@pytest.mark.asyncio
async def test_element_finder_property_raises_when_not_started():
    b = BrowserManager(headless=True)
    with pytest.raises(BrowserError, match="Browser not started"):
        _ = b.element_finder


@pytest.mark.asyncio
async def test_context_property_raises_when_not_initialized():
    b = BrowserManager(headless=True)
    with pytest.raises(BrowserError, match="Browser context not initialized"):
        _ = b.context


@pytest.mark.asyncio
async def test_navigate():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.navigate("https://example.com")
        assert result.success
        assert result.action_type == ActionType.NAVIGATE
        assert result.data["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_navigate_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        with pytest.raises(ActionFailed, match="Navigation failed"):
            await b.navigate("https://example.com")


@pytest.mark.asyncio
async def test_click():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.click("div")
        assert result.success
        assert result.action_type == ActionType.CLICK


@pytest.mark.asyncio
async def test_click_no_selector():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        with pytest.raises(ElementNotFound):
            await b.click(None)


@pytest.mark.asyncio
async def test_type_text():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.type_text("hello", "input")
        assert result.success
        assert result.action_type == ActionType.TYPE


@pytest.mark.asyncio
async def test_type_text_no_selector():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.type_text("hello world")
        assert result.success


@pytest.mark.asyncio
async def test_scroll():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.scroll(delta_y=300)
        assert result.success
        assert result.action_type == ActionType.SCROLL


@pytest.mark.asyncio
async def test_scroll_with_selector():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.scroll(delta_y=200, selector="div", strategy="css")
        assert result.success


@pytest.mark.asyncio
async def test_screenshot():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.screenshot()
        assert result.success
        assert result.action_type == ActionType.SCREENSHOT
        assert result.data["image"] == b"fake_screenshot_data"


@pytest.mark.asyncio
async def test_screenshot_jpeg():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.screenshot(type="jpeg", quality=85)
        assert result.success


@pytest.mark.asyncio
async def test_extract_text():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.extract_text()
        assert result.success
        assert result.action_type == ActionType.EXTRACT_TEXT


@pytest.mark.asyncio
async def test_extract_text_with_selector():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.extract_text("div")
        assert result.success


@pytest.mark.asyncio
async def test_extract_text_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.wait_for_selector = AsyncMock(return_value=None)
        with pytest.raises(ElementNotFound):
            await b.extract_text("nonexistent")


@pytest.mark.asyncio
async def test_extract_html():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.extract_html()
        assert result.success
        assert result.action_type == ActionType.EXTRACT_HTML


@pytest.mark.asyncio
async def test_evaluate():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.evaluate("1 + 1")
        assert result.success
        assert result.action_type == ActionType.EVALUATE


@pytest.mark.asyncio
async def test_evaluate_with_arg():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.evaluate("(x) => x * 2", arg=21)
        assert result.success


@pytest.mark.asyncio
async def test_get_url():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.get_url()
        assert result.success
        assert result.action_type == ActionType.GET_URL


@pytest.mark.asyncio
async def test_get_title():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.get_title()
        assert result.success
        assert result.action_type == ActionType.GET_TITLE
        assert result.data["title"] == "Example Domain"


@pytest.mark.asyncio
async def test_wait():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.wait(100)
        assert result.success
        assert result.action_type == ActionType.WAIT


@pytest.mark.asyncio
async def test_go_back():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.go_back()
        assert result.success


@pytest.mark.asyncio
async def test_go_forward():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.go_forward()
        assert result.success


@pytest.mark.asyncio
async def test_refresh():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.refresh()
        assert result.success


@pytest.mark.asyncio
async def test_hover():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.hover("div")
        assert result.success
        assert result.action_type == ActionType.HOVER


@pytest.mark.asyncio
async def test_press_key():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.press_key("Enter")
        assert result.success
        assert result.action_type == ActionType.PRESS_KEY


@pytest.mark.asyncio
async def test_select_option():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.select_option("select", "option1")
        assert result.success
        assert result.action_type == ActionType.SELECT_OPTION


@pytest.mark.asyncio
async def test_set_viewport():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.set_viewport(800, 600)
        assert result.success
        assert result.action_type == ActionType.SET_VIEWPORT


@pytest.mark.asyncio
async def test_inject_css():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.inject_css("body { color: red; }")
        assert result.success
        assert result.action_type == ActionType.INJECT_CSS


@pytest.mark.asyncio
async def test_get_cookies():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.get_cookies()
        assert result.success
        assert result.action_type == ActionType.GET_COOKIES


@pytest.mark.asyncio
async def test_clear_cookies():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.clear_cookies()
        assert result.success
        assert result.action_type == ActionType.CLEAR_COOKIES


@pytest.mark.asyncio
async def test_wait_for_navigation():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.wait_for_navigation()
        assert result.success


@pytest.mark.asyncio
async def test_execute_action_navigate():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
        result = await b.execute_action(request)
        assert result.success
        assert result.action_id == request.id


@pytest.mark.asyncio
async def test_execute_action_unknown():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        request = ActionRequest(type=ActionType.DESKTOP_CLICK, params={})
        with pytest.raises(ActionFailed, match="No handler"):
            await b.execute_action(request)


@pytest.mark.asyncio
async def test_execute_action_error_returns_result():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b.navigate = AsyncMock(side_effect=RuntimeError("unexpected"))
        request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
        result = await b.execute_action(request)
        assert not result.success
        assert "unexpected" in result.error


@pytest.mark.asyncio
async def test_action_map_completeness():
    b = BrowserManager(headless=True)
    action_map = b._action_map()
    expected = [
        ActionType.NAVIGATE, ActionType.CLICK, ActionType.TYPE, ActionType.SCROLL,
        ActionType.SCREENSHOT, ActionType.WAIT, ActionType.EXTRACT_TEXT, ActionType.EXTRACT_HTML,
        ActionType.HOVER, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK,
        ActionType.GO_BACK, ActionType.GO_FORWARD, ActionType.REFRESH,
        ActionType.GET_URL, ActionType.GET_TITLE, ActionType.EVALUATE,
        ActionType.PRESS_KEY, ActionType.SELECT_OPTION, ActionType.SET_VIEWPORT,
        ActionType.INJECT_CSS, ActionType.GET_COOKIES, ActionType.CLEAR_COOKIES,
    ]
    for at in expected:
        assert at in action_map, f"Missing action type: {at}"
    assert len(action_map) == len(expected)


@pytest.mark.asyncio
async def test_browser_type_name():
    b = BrowserManager(headless=True, browser_type=BrowserType.FIREFOX)
    assert b.browser_type_name == "firefox"
    b2 = BrowserManager(headless=True, browser_type=BrowserType.WEBKIT)
    assert b2.browser_type_name == "webkit"


@pytest.mark.asyncio
async def test_metrics_accumulation():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        await b.navigate("https://example.com")
        assert b.metrics["pages_loaded"] >= 1


@pytest.mark.asyncio
async def test_event_handlers():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        await b._on_response(MagicMock(status=404))

        assert b.metrics["errors"] == 1
        await b._on_response(MagicMock(status=200))
        assert b.metrics["errors"] == 1


@pytest.mark.asyncio
async def test_cleanup_handles_errors():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.close = AsyncMock(side_effect=Exception("Close error"))
        await b.stop()
        assert b._page is None


@pytest.mark.asyncio
async def test_navigate_with_referer():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.navigate("https://example.com", referer="https://referer.com")
        assert result.success


@pytest.mark.asyncio
async def test_click_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        mock_elem = AsyncMock()
        mock_elem.click = AsyncMock(side_effect=Exception("Click failed"))
        b._resolve_element = AsyncMock(return_value=mock_elem)
        with pytest.raises(ActionFailed, match="Click failed"):
            await b.click("div")


@pytest.mark.asyncio
async def test_type_text_element_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._resolve_element = AsyncMock(return_value=None)
        with pytest.raises(ElementNotFound):
            await b.type_text("hello", "input")


@pytest.mark.asyncio
async def test_type_text_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        mock_elem = AsyncMock()
        mock_elem.fill = AsyncMock(side_effect=Exception("Type failed"))
        b._resolve_element = AsyncMock(return_value=mock_elem)
        with pytest.raises(ActionFailed, match="Type failed"):
            await b.type_text("hello", "input")


@pytest.mark.asyncio
async def test_scroll_with_selector_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._resolve_element = AsyncMock(return_value=None)
        result = await b.scroll(delta_y=200, selector="div")
        assert result.success


@pytest.mark.asyncio
async def test_scroll_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.evaluate = AsyncMock(side_effect=Exception("Scroll failed"))
        with pytest.raises(ActionFailed, match="Scroll failed"):
            await b.scroll()


@pytest.mark.asyncio
async def test_screenshot_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))
        with pytest.raises(ActionFailed, match="Screenshot failed"):
            await b.screenshot()


@pytest.mark.asyncio
async def test_extract_text_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.inner_text = AsyncMock(side_effect=Exception("Extract failed"))
        with pytest.raises(ActionFailed, match="Extract failed"):
            await b.extract_text()


@pytest.mark.asyncio
async def test_extract_html_with_selector():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.extract_html("div")
        assert result.success


@pytest.mark.asyncio
async def test_extract_html_with_selector_pretty():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.extract_html("div", pretty=True)
        assert result.success


@pytest.mark.asyncio
async def test_extract_html_element_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._resolve_element = AsyncMock(return_value=None)
        with pytest.raises(ElementNotFound):
            await b.extract_html("nonexistent")


@pytest.mark.asyncio
async def test_extract_html_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.content = AsyncMock(side_effect=Exception("HTML failed"))
        with pytest.raises(ActionFailed, match="HTML failed"):
            await b.extract_html()


@pytest.mark.asyncio
async def test_evaluate_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.evaluate = AsyncMock(side_effect=Exception("Eval failed"))
        with pytest.raises(ActionFailed, match="Eval failed"):
            await b.evaluate("1 + 1")


@pytest.mark.asyncio
async def test_go_back_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.go_back = AsyncMock(side_effect=Exception("Back failed"))
        with pytest.raises(ActionFailed, match="Back failed"):
            await b.go_back()


@pytest.mark.asyncio
async def test_go_forward_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.go_forward = AsyncMock(side_effect=Exception("Forward failed"))
        with pytest.raises(ActionFailed, match="Forward failed"):
            await b.go_forward()


@pytest.mark.asyncio
async def test_refresh_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.reload = AsyncMock(side_effect=Exception("Refresh failed"))
        with pytest.raises(ActionFailed, match="Refresh failed"):
            await b.refresh()


@pytest.mark.asyncio
async def test_hover_element_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._resolve_element = AsyncMock(return_value=None)
        with pytest.raises(ElementNotFound):
            await b.hover("nonexistent")


@pytest.mark.asyncio
async def test_hover_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        mock_elem = AsyncMock()
        mock_elem.hover = AsyncMock(side_effect=Exception("Hover failed"))
        b._resolve_element = AsyncMock(return_value=mock_elem)
        with pytest.raises(ActionFailed, match="Hover failed"):
            await b.hover("div")


@pytest.mark.asyncio
async def test_press_key_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.keyboard.press = AsyncMock(side_effect=Exception("Press failed"))
        with pytest.raises(ActionFailed, match="Press failed"):
            await b.press_key("Enter")


@pytest.mark.asyncio
async def test_select_option_element_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._resolve_element = AsyncMock(return_value=None)
        with pytest.raises(ElementNotFound):
            await b.select_option("select", "option1")


@pytest.mark.asyncio
async def test_select_option_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        mock_elem = AsyncMock()
        mock_elem.select_option = AsyncMock(side_effect=Exception("Select failed"))
        b._resolve_element = AsyncMock(return_value=mock_elem)
        with pytest.raises(ActionFailed, match="Select failed"):
            await b.select_option("select", "option1")


@pytest.mark.asyncio
async def test_select_option_list():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b.select_option("select", ["option1", "option2"])
        assert result.success


@pytest.mark.asyncio
async def test_set_viewport_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.set_viewport_size = AsyncMock(side_effect=Exception("Viewport failed"))
        with pytest.raises(ActionFailed, match="Viewport failed"):
            await b.set_viewport(800, 600)


@pytest.mark.asyncio
async def test_inject_css_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.add_style_tag = AsyncMock(side_effect=Exception("CSS failed"))
        with pytest.raises(ActionFailed, match="CSS failed"):
            await b.inject_css("body { color: red; }")


@pytest.mark.asyncio
async def test_wait_for_navigation_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.wait_for_load_state = AsyncMock(side_effect=Exception("Nav wait failed"))
        with pytest.raises(ActionFailed, match="Nav wait failed"):
            await b.wait_for_navigation()


@pytest.mark.asyncio
async def test_get_cookies_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._context.cookies = AsyncMock(side_effect=Exception("Cookies failed"))
        with pytest.raises(ActionFailed, match="Cookies failed"):
            await b.get_cookies()


@pytest.mark.asyncio
async def test_clear_cookies_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._context.clear_cookies = AsyncMock(side_effect=Exception("Clear failed"))
        with pytest.raises(ActionFailed, match="Clear failed"):
            await b.clear_cookies()


@pytest.mark.asyncio
async def test_cleanup_error_context():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._context.close = AsyncMock(side_effect=Exception("Context close error"))
        await b.stop()
        assert b._page is None


@pytest.mark.asyncio
async def test_cleanup_error_browser():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.close = AsyncMock(return_value=None)
        b._context.close = AsyncMock(return_value=None)
        b._browser.close = AsyncMock(side_effect=Exception("Browser close error"))
        await b.stop()
        assert b._page is None


@pytest.mark.asyncio
async def test_cleanup_error_playwright():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b._page.close = AsyncMock(return_value=None)
        b._context.close = AsyncMock(return_value=None)
        b._browser.close = AsyncMock(return_value=None)
        b._playwright.stop = AsyncMock(side_effect=Exception("Playwright stop error"))
        await b.stop()
        assert b._page is None


@pytest.mark.asyncio
async def test_resolve_element_invalid_strategy():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        result = await b._resolve_element("div", "invalid_strategy")
        assert result is not None


@pytest.mark.asyncio
async def test_on_page_error():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        await b._on_page_error(ValueError("test page error"))
        assert b.metrics["errors"] == 1


@pytest.mark.asyncio
async def test_execute_action_re_raises_action_failed():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b.navigate = AsyncMock(side_effect=ActionFailed("navigate", "navigation failed"))
        request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
        with pytest.raises(ActionFailed, match="navigation failed"):
            await b.execute_action(request)


@pytest.mark.asyncio
async def test_execute_action_re_raises_element_not_found():
    b = BrowserManager(headless=True)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await b.start()
        b.navigate = AsyncMock(side_effect=ElementNotFound("div", "css", "<html></html>"))
        request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
        with pytest.raises(ElementNotFound):
            await b.execute_action(request)
