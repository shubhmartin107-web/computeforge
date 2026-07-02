from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class FindingStrategy(str, enum.Enum):
    """Strategies for locating elements on a page."""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"
    ALT_TEXT = "alt_text"
    TITLE = "title"
    COORDINATES = "coordinates"


@dataclass
class ElementCriteria:
    """Criteria for finding an element on the page."""

    strategy: FindingStrategy
    value: str
    timeout_ms: float = 5000.0
    wait_for_state: str = "visible"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ElementInfo:
    """Information about a found element."""

    tag: str
    text: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    bounding_box: dict[str, float] | None = None
    is_visible: bool = True
    is_enabled: bool = True
    inner_html: str | None = None


class ElementFinder:
    """Multi-strategy element finder with fallback support."""

    def __init__(self, page: Any):
        self._page = page

    async def find(self, criteria: ElementCriteria) -> Any | None:
        """Find an element using the specified strategy."""
        strategy_map = {
            FindingStrategy.CSS: self._find_by_css,
            FindingStrategy.XPATH: self._find_by_xpath,
            FindingStrategy.TEXT: self._find_by_text,
            FindingStrategy.ROLE: self._find_by_role,
            FindingStrategy.LABEL: self._find_by_label,
            FindingStrategy.PLACEHOLDER: self._find_by_placeholder,
            FindingStrategy.TEST_ID: self._find_by_test_id,
            FindingStrategy.ALT_TEXT: self._find_by_alt_text,
            FindingStrategy.TITLE: self._find_by_title,
            FindingStrategy.COORDINATES: self._find_by_coordinates,
        }
        finder = strategy_map.get(criteria.strategy)
        if finder is None:
            raise ValueError(f"Unknown finding strategy: {criteria.strategy}")
        return await finder(criteria)

    async def find_with_fallback(self, criteria_list: list[ElementCriteria]) -> Any | None:
        """Try multiple strategies in order until one succeeds."""
        for criteria in criteria_list:
            try:
                element = await self.find(criteria)
                if element is not None:
                    return element
            except Exception:
                continue
        return None

    async def _find_by_css(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.wait_for_selector(
                criteria.value,
                timeout=criteria.timeout_ms,
                state=criteria.wait_for_state,
            )
        except Exception:
            return None

    async def _find_by_xpath(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.wait_for_selector(
                f"xpath={criteria.value}",
                timeout=criteria.timeout_ms,
                state=criteria.wait_for_state,
            )
        except Exception:
            return None

    async def _find_by_text(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_text(criteria.value, exact=False).element_handle()
        except Exception:
            return None

    async def _find_by_role(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_role(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_label(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_label(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_placeholder(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_placeholder(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_test_id(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_test_id(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_alt_text(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_alt_text(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_title(self, criteria: ElementCriteria) -> Any | None:
        try:
            return await self._page.get_by_title(criteria.value).element_handle()
        except Exception:
            return None

    async def _find_by_coordinates(self, criteria: ElementCriteria) -> Any | None:
        try:
            coords = criteria.value.split(",")
            x, y = float(coords[0]), float(coords[1])
            handle = await self._page.evaluate_handle(
                "(args) => document.elementFromPoint(args[0], args[1])", [x, y]
            )
            if await handle.evaluate("el => el === null"):
                await handle.dispose()
                return None
            return handle
        except Exception:
            return None
