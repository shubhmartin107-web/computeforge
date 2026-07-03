"""Tests for the capability/permission system."""

from computeforge.models.capability import Capability, ParameterDef, RiskLevel
from computeforge.safety.permissions import CapabilityRegistry


def test_capability_registry_builtins():
    registry = CapabilityRegistry()
    caps = registry.list_capabilities()
    assert len(caps) >= 10
    names = [c.name for c in caps]
    assert "browser.navigate" in names
    assert "browser.click" in names
    assert "desktop.click" in names


def test_capability_risk_levels():
    registry = CapabilityRegistry()
    assert registry.get_risk_level("navigate") == RiskLevel.MEDIUM
    assert registry.get_risk_level("click") == RiskLevel.LOW
    assert registry.get_risk_level("evaluate") == RiskLevel.CRITICAL
    assert registry.get_risk_level("desktop_click") == RiskLevel.HIGH


def test_capability_permissions():
    registry = CapabilityRegistry()
    perms = registry.get_required_permissions("evaluate")
    assert "browser.evaluate" in perms
    perms = registry.get_required_permissions("screenshot")
    assert "browser.screenshot" in perms


def test_capability_register():
    registry = CapabilityRegistry()
    cap = Capability(
        name="custom.test",
        description="Custom test capability",
        action_type="custom_action",
        risk_level=RiskLevel.HIGH,
        required_permissions=["custom.permission"],
        category="custom",
    )
    registry.register(cap)
    assert registry.get("custom.test") is cap


def test_capability_get_nonexistent():
    registry = CapabilityRegistry()
    assert registry.get("nonexistent") is None


def test_capability_list_by_category():
    registry = CapabilityRegistry()
    desktop_caps = registry.list_capabilities(category="desktop")
    assert all(c.category == "desktop" for c in desktop_caps)
    assert len(desktop_caps) >= 4


def test_capability_get_risk_level_default():
    registry = CapabilityRegistry()
    assert registry.get_risk_level("unknown_action") == RiskLevel.MEDIUM


def test_capability_get_permissions_default():
    registry = CapabilityRegistry()
    assert registry.get_required_permissions("unknown_action") == []
