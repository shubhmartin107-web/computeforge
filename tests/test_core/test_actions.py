"""Tests for the core actions module."""

import pytest

from computeforge.core.actions import (
    ActionRequest,
    ActionResult,
    ActionType,
    get_action_handler,
    list_registered_actions,
    register_action,
)


def test_action_type_values():
    assert ActionType.NAVIGATE.value == "navigate"
    assert ActionType.CLICK.value == "click"
    assert ActionType.TYPE.value == "type"
    assert ActionType.SCREENSHOT.value == "screenshot"


def test_action_result():
    result = ActionResult(success=True, action_type=ActionType.NAVIGATE, data={"url": "https://example.com"}, duration_ms=100.0)
    assert result.success is True
    assert result.data["url"] == "https://example.com"
    d = result.to_dict()
    assert d["success"] is True
    assert d["action_type"] == "navigate"


def test_action_request():
    req = ActionRequest(type=ActionType.CLICK, params={"selector": "#button"})
    assert req.type == ActionType.CLICK
    assert req.params["selector"] == "#button"
    assert req.id is not None


def test_action_request_to_dict():
    req = ActionRequest(type=ActionType.CLICK, params={"selector": "#btn"})
    d = req.to_dict()
    assert d["type"] == "click"
    assert d["params"] == {"selector": "#btn"}
    assert d["id"] == req.id
    assert "created_at" in d


def test_action_registry():
    @register_action(ActionType.SCREENSHOT)
    async def test_handler(**kwargs):
        return ActionResult(success=True, action_type=ActionType.SCREENSHOT)

    handler = get_action_handler(ActionType.SCREENSHOT)
    assert handler is not None
    assert handler.__name__ == "test_handler"


def test_action_handler_not_found():
    with pytest.raises(ValueError, match="No handler registered for action type"):
        get_action_handler(ActionType.GO_BACK)


def test_list_registered_actions():
    actions = list_registered_actions()
    assert ActionType.SCREENSHOT in actions
