from computeforge.models.capability import Capability, ParameterDef, RiskLevel


def test_risk_level_values():
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"


def test_parameter_def_defaults():
    param = ParameterDef(name="test_param")
    assert param.name == "test_param"
    assert param.type == "string"
    assert param.description == ""
    assert param.required is False
    assert param.default is None
    assert param.enum_values is None


def test_parameter_def_creation():
    param = ParameterDef(
        name="mode",
        type="string",
        description="Operating mode",
        required=True,
        default="auto",
        enum_values=["auto", "manual"],
    )
    assert param.name == "mode"
    assert param.type == "string"
    assert param.description == "Operating mode"
    assert param.required is True
    assert param.default == "auto"
    assert param.enum_values == ["auto", "manual"]


def test_capability_defaults():
    cap = Capability(name="test.cap", description="A test")
    assert cap.name == "test.cap"
    assert cap.description == "A test"
    assert cap.action_type == ""
    assert cap.risk_level == RiskLevel.MEDIUM
    assert cap.required_permissions == []
    assert cap.parameters == []
    assert cap.category == "general"
    assert cap.tags == []


def test_capability_creation():
    params = [
        ParameterDef(name="url", type="string", required=True),
        ParameterDef(name="timeout", type="integer", default=30),
    ]
    cap = Capability(
        name="browser.navigate",
        description="Navigate to a URL",
        action_type="navigate",
        risk_level=RiskLevel.HIGH,
        required_permissions=["browser.navigate"],
        parameters=params,
        category="browser",
        tags=["navigation", "core"],
    )
    assert cap.name == "browser.navigate"
    assert cap.description == "Navigate to a URL"
    assert cap.action_type == "navigate"
    assert cap.risk_level == RiskLevel.HIGH
    assert cap.required_permissions == ["browser.navigate"]
    assert len(cap.parameters) == 2
    assert cap.parameters[0].name == "url"
    assert cap.parameters[1].default == 30
    assert cap.category == "browser"
    assert cap.tags == ["navigation", "core"]
