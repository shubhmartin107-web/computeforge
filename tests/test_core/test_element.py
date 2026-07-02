"""Tests for the element finding module."""

from computeforge.core.element import ElementCriteria, ElementInfo, FindingStrategy


def test_finding_strategy_values():
    assert FindingStrategy.CSS.value == "css"
    assert FindingStrategy.XPATH.value == "xpath"
    assert FindingStrategy.TEXT.value == "text"
    assert FindingStrategy.ROLE.value == "role"


def test_element_criteria():
    criteria = ElementCriteria(
        strategy=FindingStrategy.CSS,
        value="#my-button",
        timeout_ms=3000.0,
    )
    assert criteria.strategy == FindingStrategy.CSS
    assert criteria.value == "#my-button"
    assert criteria.timeout_ms == 3000.0


def test_element_info():
    info = ElementInfo(
        tag="button",
        text="Click me",
        bounding_box={"x": 10, "y": 20, "width": 100, "height": 50},
    )
    assert info.tag == "button"
    assert info.text == "Click me"
    assert info.bounding_box["width"] == 100
