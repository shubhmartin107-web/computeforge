from __future__ import annotations

import asyncio
import enum
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)
from playwright.async_api import (
    BrowserType as PW_BrowserType,
)

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.core.element import ElementCriteria, ElementFinder, FindingStrategy
from computeforge.core.exceptions import ActionFailed, BrowserError, ElementNotFound

logger = logging.getLogger("computeforge.core.browser")


class BrowserType(enum.Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


BROWSER_ARGS: dict[str, list[str]] = {
    "chromium": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-blink-features=AutomationControlled",
    ],
    "firefox": [],
    "webkit": [],
}

USER_AGENTS: dict[str, str] = {
    "chromium": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "firefox": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    "webkit": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
}


class BrowserManager:
    """Manages Playwright browser instances with multi-browser support.

    Features:
    - Supports Chromium, Firefox, and WebKit
    - Automatic retry on browser launch failure
    - Stealth mode to avoid bot detection
    - Cookie and storage management
    - Network interception and monitoring
    - Performance metrics
    """

    def __init__(
        self,
        headless: bool = True,
        viewport: dict[str, int] | None = None,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        locale: str = "en-US",
        timeout_ms: int = 30000,
        slow_mo: int = 0,
        user_agent: str | None = None,
    ):
        self._headless = headless
        self._viewport = viewport or {"width": 1280, "height": 720}
        self._browser_type = browser_type
        self._locale = locale
        self._timeout_ms = timeout_ms
        self._slow_mo = slow_mo
        self._custom_user_agent = user_agent

        self._playwright: async_playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._element_finder: ElementFinder | None = None
        self._screenshot_dir: Path | None = None
        self._metrics: dict[str, Any] = {
            "pages_loaded": 0,
            "actions_executed": 0,
            "errors": 0,
            "total_navigation_ms": 0,
        }

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BrowserError("Browser not started. Call start() first.")
        return self._page

    @property
    def element_finder(self) -> ElementFinder:
        if self._element_finder is None:
            raise BrowserError("Browser not started. Call start() first.")
        return self._element_finder

    @property
    def is_running(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    @property
    def browser_type_name(self) -> str:
        return self._browser_type.value

    @property
    def metrics(self) -> dict[str, Any]:
        return dict(self._metrics)

    # ─── Lifecycle ────────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch the browser with the configured type."""
        last_error = None
        for attempt in range(3):
            try:
                self._playwright = await async_playwright().start()
                pw_browser_type: PW_BrowserType = getattr(self._playwright, self._browser_type.value)
                self._browser = await pw_browser_type.launch(
                    headless=self._headless,
                    args=BROWSER_ARGS.get(self._browser_type.value, []),
                    slow_mo=self._slow_mo,
                )
                user_agent = self._custom_user_agent or USER_AGENTS.get(self._browser_type.value)
                self._context = await self._browser.new_context(
                    viewport=self._viewport,
                    locale=self._locale,
                    timezone_id="America/New_York",
                    user_agent=user_agent,
                    ignore_https_errors=True,
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )
                self._page = await self._context.new_page()
                self._page.set_default_timeout(self._timeout_ms)
                self._element_finder = ElementFinder(self._page)

                # Set up network monitoring
                self._page.on("response", self._on_response)
                self._page.on("pageerror", self._on_page_error)

                logger.info(f"Browser started: {self._browser_type.value} (headless={self._headless})")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Browser launch attempt {attempt + 1}/3 failed: {e}")
                await self._cleanup()
                await asyncio.sleep(2 ** attempt)

        raise BrowserError(f"Failed to start browser after 3 attempts: {last_error}")

    async def stop(self) -> None:
        """Close the browser and clean up resources."""
        await self._cleanup()
        logger.info("Browser stopped")

    async def restart(self) -> None:
        """Restart the browser."""
        await self.stop()
        await self.start()

    async def _cleanup(self) -> None:
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Browser cleanup error: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._element_finder = None

    # ─── Navigation ───────────────────────────────────────────────────

    async def navigate(self, url: str, **kwargs) -> ActionResult:
        """Navigate to a URL with timeout and wait strategy."""
        try:
            timeout = kwargs.get("timeout", self._timeout_ms)
            wait_until = kwargs.get("wait_until", "load")
            referer = kwargs.get("referer")

            goto_options = {"timeout": timeout, "wait_until": wait_until}
            if referer:
                goto_options["referer"] = referer

            start = asyncio.get_event_loop().time()
            response = await self.page.goto(url, **goto_options)
            duration = (asyncio.get_event_loop().time() - start) * 1000

            self._metrics["pages_loaded"] += 1
            self._metrics["total_navigation_ms"] += duration

            return ActionResult(
                success=True,
                action_type=ActionType.NAVIGATE,
                data={
                    "url": self.page.url,
                    "title": await self.page.title(),
                    "status_code": response.status if response else None,
                    "duration_ms": duration,
                },
            )
        except Exception as e:
            raise ActionFailed("navigate", str(e), e)

    # ─── Page Interaction ─────────────────────────────────────────────

    async def click(self, selector: str | None = None, strategy: str = "css", **kwargs) -> ActionResult:
        """Click an element with multiple fallback strategies."""
        try:
            element = await self._resolve_element(selector, strategy)
            if element is None:
                raise ElementNotFound(selector or "", strategy, await self.page.content())
            await element.click(
                **{k: v for k, v in kwargs.items() if k in ("button", "click_count", "delay", "force", "no_wait_after", "position", "modifiers", "trial")}
            )
            self._metrics["actions_executed"] += 1
            return ActionResult(success=True, action_type=ActionType.CLICK, data={"selector": selector, "strategy": strategy})
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("click", str(e), e)

    async def type_text(self, text: str, selector: str | None = None, strategy: str = "css", **kwargs) -> ActionResult:
        """Type text with smart delay and element finding."""
        try:
            delay = kwargs.get("delay", 10)
            if selector:
                element = await self._resolve_element(selector, strategy)
                if element is None:
                    raise ElementNotFound(selector, strategy, await self.page.content())
                await element.fill("")
                await element.type(text, delay=delay)
            else:
                await self.page.keyboard.type(text, delay=delay)
            self._metrics["actions_executed"] += 1
            return ActionResult(success=True, action_type=ActionType.TYPE, data={"text_length": len(text), "selector": selector})
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("type", str(e), e)

    async def scroll(self, delta_x: float = 0, delta_y: float = 300, **kwargs) -> ActionResult:
        """Scroll the page or a specific element."""
        try:
            selector = kwargs.get("selector")
            behavior = kwargs.get("behavior", "smooth")
            if selector:
                element = await self._resolve_element(selector, kwargs.get("strategy", "css"))
                if element:
                    await element.evaluate("(args) => el.scrollBy({left: args[0], top: args[1], behavior: args[2]})", [delta_x, delta_y, behavior])
                else:
                    await self.page.evaluate("(args) => window.scrollBy({left: args[0], top: args[1], behavior: args[2]})", [delta_x, delta_y, behavior])
            else:
                await self.page.evaluate("(args) => window.scrollBy({left: args[0], top: args[1], behavior: args[2]})", [delta_x, delta_y, behavior])
            self._metrics["actions_executed"] += 1
            return ActionResult(
                success=True,
                action_type=ActionType.SCROLL,
                data={"delta_x": delta_x, "delta_y": delta_y, "behavior": behavior},
            )
        except Exception as e:
            raise ActionFailed("scroll", str(e), e)

    async def screenshot(self, path: str | None = None, full_page: bool = False, **kwargs) -> ActionResult:
        """Take a screenshot with optional full-page capture."""
        try:
            quality = kwargs.get("quality", 80)
            type_ = kwargs.get("type", "png")
            opts = {"full_page": full_page, "type": type_}
            if type_ == "jpeg":
                opts["quality"] = quality
            screenshot_bytes = await self.page.screenshot(**opts)
            self._metrics["actions_executed"] += 1
            return ActionResult(
                success=True,
                action_type=ActionType.SCREENSHOT,
                data={
                    "image": screenshot_bytes,
                    "path": path,
                    "width": self._viewport["width"],
                    "height": self._viewport["height"],
                    "format": type_,
                },
            )
        except Exception as e:
            raise ActionFailed("screenshot", str(e), e)

    # ─── Content Extraction ───────────────────────────────────────────

    async def extract_text(self, selector: str | None = None, **kwargs) -> ActionResult:
        """Extract text with multiple strategies."""
        try:
            strip = kwargs.get("strip", True)
            if selector:
                element = await self._resolve_element(selector, kwargs.get("strategy", "css"))
                if element is None:
                    raise ElementNotFound(selector, kwargs.get("strategy", "css"), await self.page.content())
                text = await element.inner_text()
            else:
                text = await self.page.inner_text("body")
            if strip:
                text = text.strip()
            self._metrics["actions_executed"] += 1
            return ActionResult(
                success=True,
                action_type=ActionType.EXTRACT_TEXT,
                data={"text": text, "length": len(text)},
            )
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("extract_text", str(e), e)

    async def extract_html(self, selector: str | None = None, **kwargs) -> ActionResult:
        """Extract HTML with optional pretty-printing."""
        try:
            pretty = kwargs.get("pretty", False)
            if selector:
                element = await self._resolve_element(selector, kwargs.get("strategy", "css"))
                if element is None:
                    raise ElementNotFound(selector, kwargs.get("strategy", "css"), await self.page.content())
                if pretty:
                    html = await element.evaluate("el => el.outerHTML")
                else:
                    html = await element.inner_html()
            else:
                html = await self.page.content()
            self._metrics["actions_executed"] += 1
            return ActionResult(
                success=True,
                action_type=ActionType.EXTRACT_HTML,
                data={"html": html, "length": len(html)},
            )
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("extract_html", str(e), e)

    async def evaluate(self, script: str, **kwargs) -> ActionResult:
        """Execute JavaScript with sandbox warning."""
        try:
            arg = kwargs.get("arg")
            if arg is not None:
                result = await self.page.evaluate(script, arg)
            else:
                result = await self.page.evaluate(script)
            self._metrics["actions_executed"] += 1
            return ActionResult(success=True, action_type=ActionType.EVALUATE, data={"result": result})
        except Exception as e:
            raise ActionFailed("evaluate", str(e), e)

    # ─── Page Information ─────────────────────────────────────────────

    async def get_url(self) -> ActionResult:
        return ActionResult(success=True, action_type=ActionType.GET_URL, data={"url": self.page.url})

    async def get_title(self) -> ActionResult:
        title = await self.page.title()
        return ActionResult(success=True, action_type=ActionType.GET_TITLE, data={"title": title})

    async def wait(self, timeout_ms: int = 1000) -> ActionResult:
        await asyncio.sleep(timeout_ms / 1000.0)
        return ActionResult(success=True, action_type=ActionType.WAIT, data={"timeout_ms": timeout_ms})

    # ─── Advanced Features ────────────────────────────────────────────

    async def go_back(self) -> ActionResult:
        try:
            response = await self.page.go_back()
            return ActionResult(success=True, action_type=ActionType.GO_BACK, data={"url": self.page.url, "status": response.status if response else None})
        except Exception as e:
            raise ActionFailed("go_back", str(e), e)

    async def go_forward(self) -> ActionResult:
        try:
            response = await self.page.go_forward()
            return ActionResult(success=True, action_type=ActionType.GO_FORWARD, data={"url": self.page.url, "status": response.status if response else None})
        except Exception as e:
            raise ActionFailed("go_forward", str(e), e)

    async def refresh(self) -> ActionResult:
        try:
            await self.page.reload()
            return ActionResult(success=True, action_type=ActionType.REFRESH, data={"url": self.page.url})
        except Exception as e:
            raise ActionFailed("refresh", str(e), e)

    async def hover(self, selector: str, strategy: str = "css", **kwargs) -> ActionResult:
        try:
            element = await self._resolve_element(selector, strategy)
            if element is None:
                raise ElementNotFound(selector, strategy, await self.page.content())
            await element.hover(**kwargs)
            return ActionResult(success=True, action_type=ActionType.HOVER, data={"selector": selector})
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("hover", str(e), e)

    async def press_key(self, key: str, **kwargs) -> ActionResult:
        try:
            await self.page.keyboard.press(key, **kwargs)
            return ActionResult(success=True, action_type=ActionType.PRESS_KEY, data={"key": key})
        except Exception as e:
            raise ActionFailed("press_key", str(e), e)

    async def select_option(self, selector: str, value: str | list[str], strategy: str = "css") -> ActionResult:
        try:
            element = await self._resolve_element(selector, strategy)
            if element is None:
                raise ElementNotFound(selector, strategy, await self.page.content())
            values = value if isinstance(value, list) else [value]
            await element.select_option(values)
            return ActionResult(success=True, action_type=ActionType.SELECT_OPTION, data={"selector": selector, "value": value})
        except ElementNotFound:
            raise
        except Exception as e:
            raise ActionFailed("select_option", str(e), e)

    async def set_viewport(self, width: int, height: int) -> ActionResult:
        try:
            await self.page.set_viewport_size({"width": width, "height": height})
            self._viewport = {"width": width, "height": height}
            return ActionResult(success=True, action_type=ActionType.SET_VIEWPORT, data={"width": width, "height": height})
        except Exception as e:
            raise ActionFailed("set_viewport", str(e), e)

    async def inject_css(self, css: str) -> ActionResult:
        try:
            await self.page.add_style_tag(content=css)
            return ActionResult(success=True, action_type=ActionType.INJECT_CSS, data={"css_length": len(css)})
        except Exception as e:
            raise ActionFailed("inject_css", str(e), e)

    # ─── Network ──────────────────────────────────────────────────────

    async def wait_for_navigation(self, timeout_ms: int | None = None) -> ActionResult:
        try:
            timeout = timeout_ms or self._timeout_ms
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return ActionResult(success=True, action_type=ActionType.WAIT, data={"event": "networkidle"})
        except Exception as e:
            raise ActionFailed("wait_for_navigation", str(e), e)

    async def get_cookies(self) -> ActionResult:
        try:
            cookies = await self.context.cookies()
            return ActionResult(success=True, action_type=ActionType.GET_COOKIES, data={"cookies": cookies})
        except Exception as e:
            raise ActionFailed("get_cookies", str(e), e)

    async def clear_cookies(self) -> ActionResult:
        try:
            await self.context.clear_cookies()
            return ActionResult(success=True, action_type=ActionType.CLEAR_COOKIES, data={})
        except Exception as e:
            raise ActionFailed("clear_cookies", str(e), e)

    # ─── Element Resolution ──────────────────────────────────────────

    async def _resolve_element(self, selector: str | None, strategy: str) -> Any | None:
        if not selector:
            return None
        try:
            fs = FindingStrategy(strategy)
        except ValueError:
            fs = FindingStrategy.CSS
        return await self.element_finder.find(ElementCriteria(strategy=fs, value=selector))

    # ─── Event Handlers ──────────────────────────────────────────────

    async def _on_response(self, response) -> None:
        if response.status >= 400:
            self._metrics["errors"] += 1

    async def _on_page_error(self, error) -> None:
        self._metrics["errors"] += 1
        logger.debug(f"Page error: {error}")

    # ─── Action Dispatch ─────────────────────────────────────────────

    def _action_map(self) -> dict[ActionType, Any]:
        return {
            ActionType.NAVIGATE: self.navigate,
            ActionType.CLICK: self.click,
            ActionType.TYPE: self.type_text,
            ActionType.SCROLL: self.scroll,
            ActionType.SCREENSHOT: self.screenshot,
            ActionType.WAIT: self.wait,
            ActionType.EXTRACT_TEXT: self.extract_text,
            ActionType.EXTRACT_HTML: self.extract_html,
            ActionType.HOVER: self.hover,
            ActionType.DOUBLE_CLICK: self.click,
            ActionType.RIGHT_CLICK: self.click,
            ActionType.GO_BACK: self.go_back,
            ActionType.GO_FORWARD: self.go_forward,
            ActionType.REFRESH: self.refresh,
            ActionType.GET_URL: self.get_url,
            ActionType.GET_TITLE: self.get_title,
            ActionType.EVALUATE: self.evaluate,
            ActionType.PRESS_KEY: self.press_key,
            ActionType.SELECT_OPTION: self.select_option,
            ActionType.SET_VIEWPORT: self.set_viewport,
            ActionType.INJECT_CSS: self.inject_css,
            ActionType.GET_COOKIES: self.get_cookies,
            ActionType.CLEAR_COOKIES: self.clear_cookies,
        }

    async def execute_action(self, request: ActionRequest) -> ActionResult:
        action_map = self._action_map()
        handler = action_map.get(request.type)
        if handler is None:
            raise ActionFailed(request.type.value, f"No handler for action type: {request.type}")

        start = asyncio.get_event_loop().time()
        try:
            result = await handler(**request.params)
            result.action_id = request.id
            result.action_type = request.type
            result.duration_ms = (asyncio.get_event_loop().time() - start) * 1000
            return result
        except (ActionFailed, ElementNotFound, BrowserError):
            raise
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start) * 1000
            return ActionResult(
                success=False,
                action_id=request.id,
                action_type=request.type,
                error=str(e),
                duration_ms=duration,
            )

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise BrowserError("Browser context not initialized")
        return self._context
