"""Tests for the exceptions module."""

from computeforge.core.exceptions import (
    ActionFailed,
    BrowserError,
    ComputeForgeError,
    ElementNotFound,
    SafetyBlocked,
    SessionNotFound,
)


def test_base_exception():
    assert issubclass(ActionFailed, ComputeForgeError)
    assert issubclass(ElementNotFound, ComputeForgeError)
    assert issubclass(SafetyBlocked, ComputeForgeError)


def test_action_failed():
    exc = ActionFailed("navigate", "Connection refused")
    assert exc.action_type == "navigate"
    assert exc.reason == "Connection refused"
    assert "navigate" in str(exc)


def test_element_not_found():
    exc = ElementNotFound("#missing", "css")
    assert exc.selector == "#missing"
    assert exc.strategy == "css"


def test_safety_blocked():
    exc = SafetyBlocked("evaluate", "JavaScript execution blocked", policy="default")
    assert exc.action_type == "evaluate"
    assert exc.policy == "default"


def test_session_not_found():
    exc = SessionNotFound("Session abc-123 not found")
    assert "abc-123" in str(exc)


def test_browser_error():
    exc = BrowserError("Failed to launch browser")
    assert "browser" in str(exc).lower()
