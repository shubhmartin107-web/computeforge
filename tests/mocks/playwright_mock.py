from __future__ import annotations

from typing import Any


class MockElementHandle:
    def __init__(self, tag: str = "div", text: str = "", visible: bool = True):
        self._tag = tag
        self._text = text
        self._visible = visible
        self._bounding_box = {"x": 0, "y": 0, "width": 100, "height": 50}
        self._clicked = False
        self._hovered = False
        self._filled_text = ""
        self._typed_text = ""
        self._selected_values: list[str] = []
        self._inner_text = text
        self._inner_html = f"<{tag}>{text}</{tag}>"

    async def click(self, **kwargs) -> None:
        self._clicked = True

    async def hover(self, **kwargs) -> None:
        self._hovered = True

    async def fill(self, text: str) -> None:
        self._filled_text = text

    async def type(self, text: str, delay: int = 0) -> None:
        self._typed_text = text

    async def inner_text(self) -> str:
        return self._inner_text

    async def inner_html(self) -> str:
        return self._inner_html

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        if "elementFromPoint" in expression:
            return self
        if "scrollBy" in expression:
            return None
        if "outerHTML" in expression:
            return self._inner_html
        if "el === null" in expression:
            return False
        return None

    async def select_option(self, values: list[str]) -> None:
        self._selected_values = values

    async def is_visible(self) -> bool:
        return self._visible

    async def is_enabled(self) -> bool:
        return True

    async def bounding_box(self) -> dict[str, float]:
        return self._bounding_box

    async def get_attribute(self, name: str) -> str | None:
        return None

    async def dispose(self) -> None:
        pass


class MockPage:
    def __init__(self, url: str = "https://example.com", title: str = "Example Domain"):
        self._url = url
        self._title = title
        self._closed = False
        self._content = "<html><body><div>Example Domain</div></body></html>"
        self._cookies: list[dict[str, Any]] = []
        self.keyboard = MockKeyboard()
        self._viewport_size = {"width": 1280, "height": 720}

    def is_closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        self._closed = True

    async def goto(self, url: str, **kwargs) -> MockResponse | None:
        self._url = url
        return MockResponse(200)

    async def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        return self._url

    async def content(self) -> str:
        return self._content

    async def inner_text(self, selector: str) -> str:
        return "Example Domain"

    async def screenshot(self, **kwargs) -> bytes:
        return b"fake_screenshot_data"

    async def set_viewport_size(self, viewport: dict[str, int]) -> None:
        self._viewport_size = viewport

    def set_default_timeout(self, timeout: int) -> None:
        pass

    async def wait_for_selector(self, selector: str, **kwargs) -> MockElementHandle:
        return MockElementHandle()

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        if "elementFromPoint" in expression:
            return None
        if "scrollBy" in expression:
            return None
        if "navigator.webdriver" in expression:
            return None
        return None

    async def evaluate_handle(self, expression: str, arg: Any = None) -> MockElementHandle:
        return MockElementHandle()

    def get_by_text(self, text: str, exact: bool = False) -> MockLocator:
        return MockLocator()

    def get_by_role(self, role: str) -> MockLocator:
        return MockLocator()

    def get_by_label(self, label: str) -> MockLocator:
        return MockLocator()

    def get_by_placeholder(self, placeholder: str) -> MockLocator:
        return MockLocator()

    def get_by_test_id(self, test_id: str) -> MockLocator:
        return MockLocator()

    def get_by_alt_text(self, alt_text: str) -> MockLocator:
        return MockLocator()

    def get_by_title(self, title: str) -> MockLocator:
        return MockLocator()

    def on(self, event: str, handler: Any) -> None:
        pass

    async def go_back(self) -> MockResponse | None:
        return MockResponse(200)

    async def go_forward(self) -> MockResponse | None:
        return MockResponse(200)

    async def reload(self) -> MockResponse | None:
        return MockResponse(200)

    async def add_style_tag(self, content: str) -> None:
        pass

    async def wait_for_load_state(self, state: str, timeout: int | None = None) -> None:
        pass


class MockLocator:
    async def element_handle(self) -> MockElementHandle:
        return MockElementHandle()


class MockKeyboard:
    async def type(self, text: str, delay: int = 0) -> None:
        pass

    async def press(self, key: str, **kwargs) -> None:
        pass


class MockResponse:
    def __init__(self, status: int = 200):
        self.status = status


class MockBrowserContext:
    def __init__(self):
        self._cookies: list[dict[str, Any]] = []

    async def new_page(self) -> MockPage:
        return MockPage()

    async def close(self) -> None:
        pass

    async def cookies(self) -> list[dict[str, Any]]:
        return self._cookies

    async def clear_cookies(self) -> None:
        self._cookies = []


class MockBrowser:
    async def new_context(self, **kwargs) -> MockBrowserContext:
        return MockBrowserContext()

    async def close(self) -> None:
        pass

    @property
    def is_connected(self) -> bool:
        return True


class MockPlaywright:
    async def start(self) -> MockPlaywright:
        return self

    async def stop(self) -> None:
        pass

    @property
    def chromium(self) -> MockBrowserType:
        return MockBrowserType()

    @property
    def firefox(self) -> MockBrowserType:
        return MockBrowserType()

    @property
    def webkit(self) -> MockBrowserType:
        return MockBrowserType()


class MockBrowserType:
    async def launch(self, **kwargs) -> MockBrowser:
        return MockBrowser()
