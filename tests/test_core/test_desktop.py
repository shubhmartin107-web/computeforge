from __future__ import annotations

from unittest.mock import patch

import pytest

from computeforge.core.actions import ActionType
from computeforge.core.desktop import (
    DesktopBackendType,
    MSSController,
    PlaywrightDesktopController,
    PyAutoGUIController,
    create_desktop_controller,
)


@pytest.mark.asyncio
async def test_desktop_backend_type_values():
    assert DesktopBackendType.PYAUTOGUI.value == "pyautogui"
    assert DesktopBackendType.MSS.value == "mss"
    assert DesktopBackendType.PLAYWRIGHT.value == "playwright"


@pytest.mark.asyncio
async def test_create_pyautogui_controller():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    assert isinstance(ctrl, PyAutoGUIController)


@pytest.mark.asyncio
async def test_create_mss_controller():
    ctrl = create_desktop_controller(DesktopBackendType.MSS)
    assert isinstance(ctrl, MSSController)


@pytest.mark.asyncio
async def test_create_playwright_controller():
    ctrl = create_desktop_controller(DesktopBackendType.PLAYWRIGHT)
    assert isinstance(ctrl, PlaywrightDesktopController)


@pytest.mark.asyncio
async def test_create_unknown_backend():
    with pytest.raises(ValueError, match="Unsupported desktop backend"):
        create_desktop_controller("unknown")


@pytest.mark.asyncio
async def test_pyautogui_click():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.click") as mock_click:
        result = await ctrl.click(100, 200)
        assert result.success
        assert result.action_type == ActionType.DESKTOP_CLICK
        mock_click.assert_called_once_with(100, 200, button="left")


@pytest.mark.asyncio
async def test_pyautogui_click_failure():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.click", side_effect=Exception("Click failed")):
        result = await ctrl.click(100, 200)
        assert not result.success


@pytest.mark.asyncio
async def test_pyautogui_type_text():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.write") as mock_write:
        result = await ctrl.type_text("hello", delay=10)
        assert result.success
        assert result.action_type == ActionType.DESKTOP_TYPE
        mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_pyautogui_move_mouse():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.moveTo") as mock_move:
        result = await ctrl.move_mouse(100, 200)
        assert result.success
        assert result.action_type == ActionType.DESKTOP_MOVE
        mock_move.assert_called_once_with(100, 200)


@pytest.mark.asyncio
async def test_pyautogui_screenshot():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.screenshot") as mock_ss:
        mock_img = mock_ss.return_value
        mock_img.save = lambda _buf, **_kw: None
        result = await ctrl.screenshot()
        assert result.success
        assert result.action_type == ActionType.DESKTOP_SCREENSHOT


@pytest.mark.asyncio
async def test_pyautogui_press_key():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.press") as mock_press:
        result = await ctrl.press_key("enter")
        assert result.success
        assert result.action_type == ActionType.DESKTOP_KEYPRESS
        mock_press.assert_called_once_with("enter")


@pytest.mark.asyncio
async def test_pyautogui_scroll():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.scroll") as mock_scroll:
        result = await ctrl.scroll(3)
        assert result.success
        assert result.action_type == ActionType.DESKTOP_SCROLL
        mock_scroll.assert_called_once_with(3)


@pytest.mark.asyncio
async def test_mss_screenshot():
    ctrl = create_desktop_controller(DesktopBackendType.MSS)
    with patch("mss.mss") as mock_mss:
        instance = mock_mss.return_value.__enter__.return_value
        mock_img = instance.grab.return_value
        mock_img.size = (100, 100)
        mock_img.rgb = b"x" * 30000
        result = await ctrl.screenshot()
        assert result.success
        assert result.action_type == ActionType.DESKTOP_SCREENSHOT


@pytest.mark.asyncio
async def test_mss_screenshot_failure():
    ctrl = create_desktop_controller(DesktopBackendType.MSS)
    with patch("mss.mss", side_effect=Exception("MSS failed")):
        result = await ctrl.screenshot()
        assert not result.success


@pytest.mark.asyncio
async def test_playwright_screenshot():
    from tests.mocks.playwright_mock import MockPage
    page = MockPage()
    ctrl = PlaywrightDesktopController(page=page)
    result = await ctrl.screenshot()
    assert result.success
    assert result.action_type == ActionType.DESKTOP_SCREENSHOT


@pytest.mark.asyncio
async def test_playwright_screenshot_no_page():
    ctrl = PlaywrightDesktopController()
    result = await ctrl.screenshot()
    assert not result.success


@pytest.mark.asyncio
async def test_playwright_screenshot_with_region():
    from tests.mocks.playwright_mock import MockPage
    page = MockPage()
    ctrl = PlaywrightDesktopController(page=page)
    result = await ctrl.screenshot(region=(0, 0, 100, 100))
    assert result.success


@pytest.mark.asyncio
async def test_pyautogui_screenshot_failure():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.screenshot", side_effect=Exception("SS failed")):
        result = await ctrl.screenshot()
        assert not result.success


@pytest.mark.asyncio
async def test_mss_screenshot_with_region():
    ctrl = create_desktop_controller(DesktopBackendType.MSS)
    with patch("mss.mss") as mock_mss:
        instance = mock_mss.return_value.__enter__.return_value
        mock_img = instance.grab.return_value
        mock_img.size = (50, 50)
        mock_img.rgb = b"x" * 7500
        result = await ctrl.screenshot(region=(0, 0, 50, 50))
        assert result.success
        assert result.action_type == ActionType.DESKTOP_SCREENSHOT


@pytest.mark.asyncio
async def test_pyautogui_all_methods_error():
    ctrl = create_desktop_controller(DesktopBackendType.PYAUTOGUI)
    with patch("pyautogui.click", side_effect=Exception("fail")):
        result = await ctrl.click(100, 100)
        assert not result.success
    with patch("pyautogui.write", side_effect=Exception("fail")):
        result = await ctrl.type_text("x")
        assert not result.success
    with patch("pyautogui.moveTo", side_effect=Exception("fail")):
        result = await ctrl.move_mouse(100, 100)
        assert not result.success
    with patch("pyautogui.press", side_effect=Exception("fail")):
        result = await ctrl.press_key("enter")
        assert not result.success
    with patch("pyautogui.scroll", side_effect=Exception("fail")):
        result = await ctrl.scroll(1)
        assert not result.success
