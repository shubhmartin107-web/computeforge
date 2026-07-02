from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from computeforge.core.element import ElementCriteria, ElementFinder, ElementInfo, FindingStrategy
from tests.mocks.playwright_mock import MockElementHandle, MockPage


@pytest.fixture
def finder():
    return ElementFinder(MockPage())


@pytest.mark.asyncio
async def test_finding_strategy_values():
    assert FindingStrategy.CSS.value == "css"
    assert FindingStrategy.XPATH.value == "xpath"
    assert FindingStrategy.TEXT.value == "text"
    assert FindingStrategy.ROLE.value == "role"
    assert FindingStrategy.LABEL.value == "label"
    assert FindingStrategy.PLACEHOLDER.value == "placeholder"
    assert FindingStrategy.TEST_ID.value == "test_id"
    assert FindingStrategy.ALT_TEXT.value == "alt_text"
    assert FindingStrategy.TITLE.value == "title"
    assert FindingStrategy.COORDINATES.value == "coordinates"


@pytest.mark.asyncio
async def test_find_by_css(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.CSS, value="div")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_css_not_found(finder):
    finder._page.wait_for_selector = AsyncMock(return_value=None)
    criteria = ElementCriteria(strategy=FindingStrategy.CSS, value="nonexistent")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_xpath(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.XPATH, value="//div")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_text(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.TEXT, value="hello")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_role(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.ROLE, value="button")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_label(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.LABEL, value="username")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_placeholder(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.PLACEHOLDER, value="Search...")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_test_id(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.TEST_ID, value="submit-btn")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_alt_text(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.ALT_TEXT, value="logo")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_title(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.TITLE, value="Main heading")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_coordinates(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.COORDINATES, value="100,200")
    element = await finder.find(criteria)
    assert element is not None


@pytest.mark.asyncio
async def test_find_by_coordinates_empty(finder):
    finder._page.evaluate_handle = AsyncMock(return_value=MockElementHandle())
    finder._page.evaluate_handle.return_value.evaluate = AsyncMock(return_value=True)
    criteria = ElementCriteria(strategy=FindingStrategy.COORDINATES, value="0,0")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_unknown_strategy(finder):
    criteria = ElementCriteria(strategy="unknown", value="test")
    with pytest.raises(ValueError, match="Unknown finding strategy"):
        await finder.find(criteria)


@pytest.mark.asyncio
async def test_find_with_fallback(finder):
    criterias = [
        ElementCriteria(strategy=FindingStrategy.CSS, value="nonexistent"),
        ElementCriteria(strategy=FindingStrategy.TEXT, value="hello"),
    ]
    element = await finder.find_with_fallback(criterias)
    assert element is not None


@pytest.mark.asyncio
async def test_find_with_fallback_all_fail(finder):
    finder._page.wait_for_selector = AsyncMock(side_effect=Exception("fail"))
    finder._page.get_by_text = AsyncMock(side_effect=Exception("fail"))
    criterias = [
        ElementCriteria(strategy=FindingStrategy.CSS, value="nonexistent"),
        ElementCriteria(strategy=FindingStrategy.XPATH, value="//missing"),
    ]
    element = await finder.find_with_fallback(criterias)
    assert element is None


@pytest.mark.asyncio
async def test_element_criteria_defaults():
    c = ElementCriteria(strategy=FindingStrategy.CSS, value="div")
    assert c.timeout_ms == 5000.0
    assert c.wait_for_state == "visible"
    assert c.context == {}


@pytest.mark.asyncio
async def test_element_info_defaults():
    info = ElementInfo(tag="div")
    assert info.tag == "div"
    assert info.text == ""
    assert info.attributes == {}
    assert info.bounding_box is None
    assert info.is_visible
    assert info.is_enabled
    assert info.inner_html is None


@pytest.mark.asyncio
async def test_find_by_text_not_found(finder):
    finder._page.get_by_text = MagicMock(return_value=MagicMock())
    finder._page.get_by_text.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.TEXT, value="nothing")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_coordinates_bad_input(finder):
    criteria = ElementCriteria(strategy=FindingStrategy.COORDINATES, value="not-a-number")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_role_not_found(finder):
    finder._page.get_by_role = MagicMock(return_value=MagicMock())
    finder._page.get_by_role.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.ROLE, value="button")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_label_not_found(finder):
    finder._page.get_by_label = MagicMock(return_value=MagicMock())
    finder._page.get_by_label.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.LABEL, value="username")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_placeholder_not_found(finder):
    finder._page.get_by_placeholder = MagicMock(return_value=MagicMock())
    finder._page.get_by_placeholder.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.PLACEHOLDER, value="Search...")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_test_id_not_found(finder):
    finder._page.get_by_test_id = MagicMock(return_value=MagicMock())
    finder._page.get_by_test_id.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.TEST_ID, value="submit-btn")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_alt_text_not_found(finder):
    finder._page.get_by_alt_text = MagicMock(return_value=MagicMock())
    finder._page.get_by_alt_text.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.ALT_TEXT, value="logo")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_by_title_not_found(finder):
    finder._page.get_by_title = MagicMock(return_value=MagicMock())
    finder._page.get_by_title.return_value.element_handle = AsyncMock(side_effect=Exception("not found"))
    criteria = ElementCriteria(strategy=FindingStrategy.TITLE, value="Main heading")
    element = await finder.find(criteria)
    assert element is None


@pytest.mark.asyncio
async def test_find_with_fallback_skips_exceptions(finder):
    criteria = ElementCriteria(strategy="unknown", value="test")
    element = await finder.find_with_fallback([criteria])
    assert element is None
