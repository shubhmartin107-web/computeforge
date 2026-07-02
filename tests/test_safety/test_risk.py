"""Tests for the risk assessment system."""

from computeforge.core.actions import ActionRequest, ActionType
from computeforge.safety.permissions import CapabilityRegistry
from computeforge.safety.risk import RiskScorer


def test_risk_scorer_navigate():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    level, score, _reason = scorer.assess(req)
    assert level.value == "medium"
    assert 0.3 <= score <= 0.5


def test_risk_scorer_file_url():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "file:///etc/passwd"})
    _level, score, reason = scorer.assess(req)
    assert score >= 0.7
    assert "Local file access" in reason


def test_risk_scorer_evaluate():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "document.cookie"})
    level, score, _reason = scorer.assess(req)
    assert level.value == "critical"
    assert score >= 0.9


def test_risk_scorer_safe_action():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.SCREENSHOT, params={})
    level, score, _reason = scorer.assess(req)
    assert level.value == "low"
    assert score <= 0.2


def test_risk_scorer_private_network():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "http://192.168.1.1/admin"})
    _level, score, reason = scorer.assess(req)
    assert "Private network" in reason or score >= 0.3


def test_risk_scorer_password_selector():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.TYPE, params={"selector": "input[name=\"password\"]", "value": "secret"})
    _level, score, reason = scorer.assess(req)
    assert "Password field detected" in reason
    assert score >= 0.7


def test_risk_scorer_desktop_action():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.DESKTOP_CLICK, params={"x": 100, "y": 200})
    _level, score, _reason = scorer.assess(req)
    assert score >= 0.8


def test_risk_scorer_assess_url_direct():
    scorer = RiskScorer(CapabilityRegistry())
    score = scorer.assess_url("chrome://settings")
    assert score >= 0.9


def test_risk_scorer_navigate_url_dangerous():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "javascript:alert(1)"})
    _level, score, reason = scorer.assess(req)
    assert "JavaScript URL" in reason
    assert score >= 0.9


def test_risk_scorer_navigate_localhost():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "http://localhost:3000"})
    _level, score, reason = scorer.assess(req)
    assert "Localhost access" in reason


def test_risk_scorer_script_dangerous_apis():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "eval(document.cookie); require('fs'); process.exit()"})
    _level, score, reason = scorer.assess(req)
    assert "Eval usage" in reason
    assert "Cookie access" in reason
    assert "Process access" in reason


def test_risk_scorer_script_file_access():
    scorer = RiskScorer(CapabilityRegistry())
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "fetch('file:///etc/passwd')"})
    _level, score, reason = scorer.assess(req)
    assert "File access" in reason
