from unittest.mock import patch

import pytest
import yaml

from computeforge.core.actions import ActionRequest, ActionType
from computeforge.core.exceptions import SafetyBlocked
from computeforge.safety.policies import (
    DomainRule,
    Policy,
    PolicyDecision,
    PolicyEngine,
    PolicyRule,
    RateLimitRule,
    RateLimiter,
)


def test_policy_engine_default():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.ALLOW


def test_policy_engine_block_evaluate():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "alert(1)"})
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.DENY


def test_policy_engine_decision_info():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.SCREENSHOT)
    info = engine.get_decision_for_action(req)
    assert info["allowed"] is True
    assert info["decision"] == "allow"
    assert "risk_score" in info


def test_policy_engine_check_allowed():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    engine.check(req)


def test_policy_engine_check_blocked():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "alert(1)"})
    try:
        engine.check(req)
        raise AssertionError("Should have raised SafetyBlocked")
    except SafetyBlocked:
        pass


def test_rate_limiter_no_limit():
    limiter = RateLimiter()
    limiter.check("s1", None)


def test_rate_limiter_per_minute_exceeded():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=2, max_actions_per_session=100)
    limiter.check("s1", rule)
    limiter.record_action("s1")
    limiter.check("s1", rule)
    limiter.record_action("s1")
    with pytest.raises(SafetyBlocked, match="Rate limit exceeded"):
        limiter.check("s1", rule)


def test_rate_limiter_session_limit_exceeded():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=100, max_actions_per_session=2)
    limiter.check("s1", rule)
    limiter.record_action("s1")
    limiter.check("s1", rule)
    limiter.record_action("s1")
    with pytest.raises(SafetyBlocked, match="Session action limit exceeded"):
        limiter.check("s1", rule)


def test_rate_limiter_reset():
    limiter = RateLimiter()
    limiter.record_action("s1")
    limiter.reset("s1")
    rule = RateLimitRule(max_actions_per_minute=1, max_actions_per_session=1)
    limiter.check("s1", rule)


def test_audit_log_property():
    engine = PolicyEngine()
    assert engine.audit_log == []


def test_add_policy():
    engine = PolicyEngine()
    p = Policy(name="custom")
    engine.add_policy(p)
    assert engine.get_policy("custom") is p


def test_get_policy_nonexistent():
    engine = PolicyEngine()
    assert engine.get_policy("nonexistent") is None


def test_remove_policy():
    engine = PolicyEngine()
    p = Policy(name="custom")
    engine.add_policy(p)
    engine.remove_policy("custom")
    assert engine.get_policy("custom") is None


def test_remove_policy_nonexistent():
    engine = PolicyEngine()
    engine.remove_policy("nonexistent")


def test_list_policies():
    engine = PolicyEngine()
    engine.add_policy(Policy(name="p1"))
    engine.add_policy(Policy(name="p2"))
    names = [p.name for p in engine.list_policies()]
    assert "default" in names
    assert "p1" in names
    assert "p2" in names


def test_get_audit_log():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    engine.check(req)
    log = engine.get_audit_log()
    assert len(log) == 1
    assert log[0]["action_type"] == "navigate"


def test_get_audit_log_limit():
    engine = PolicyEngine()
    for _ in range(10):
        engine.check(ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"}))
    log = engine.get_audit_log(limit=3)
    assert len(log) == 3


def test_clear_audit_log():
    engine = PolicyEngine()
    engine.check(ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"}))
    engine.clear_audit_log()
    assert engine.audit_log == []


def test_set_policy_dir_not_exists():
    engine = PolicyEngine()
    engine.set_policy_dir("/nonexistent/path_12345_test")
    assert engine._policy_dir is not None


def test_set_policy_dir_exists(tmp_path):
    engine = PolicyEngine()
    d = tmp_path / "policies"
    d.mkdir()
    engine.set_policy_dir(str(d))
    assert engine._policy_dir == d


def test_load_policies_from_dir_no_dir():
    engine = PolicyEngine()
    count = engine.load_policies_from_dir()
    assert count == 0


def test_load_policies_from_dir_empty(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    count = engine.load_policies_from_dir()
    assert count == 0


def test_load_policies_from_dir_with_yaml(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    policy_file = tmp_path / "test.yaml"
    data = {
        "policies": [
            {
                "name": "test_policy",
                "description": "Test",
                "version": "2.0",
                "rules": [{"action_type": "navigate", "risk_threshold": "low", "decision": "deny"}],
                "domain_rules": [{"pattern": "*.example.com", "allow": False}],
                "rate_limit": {"max_actions_per_minute": 10, "max_actions_per_session": 50},
                "default_decision": "deny",
                "enabled": False,
            }
        ]
    }
    policy_file.write_text(yaml.dump(data))
    count = engine.load_policies_from_dir()
    assert count == 1
    p = engine.get_policy("test_policy")
    assert p is not None
    assert p.version == "2.0"
    assert p.default_decision == PolicyDecision.DENY
    assert p.enabled is False
    assert len(p.rules) == 1
    assert len(p.domain_rules) == 1
    assert p.rate_limit is not None
    assert p.rate_limit.max_actions_per_minute == 10


def test_load_policy_file_empty(tmp_path):
    engine = PolicyEngine()
    path = str(tmp_path / "empty.yaml")
    with open(path, "w") as f:
        f.write("")
    engine.load_policy_file(path)


def test_load_policy_file_no_policies(tmp_path):
    engine = PolicyEngine()
    path = str(tmp_path / "no_policies.yaml")
    with open(path, "w") as f:
        f.write(yaml.dump({"not_policies": []}))
    engine.load_policy_file(path)


def test_load_policy_file_dict_rules(tmp_path):
    engine = PolicyEngine()
    path = str(tmp_path / "dict_rules.yaml")
    data = {
        "policies": [
            {
                "name": "dict_rules_policy",
                "rules": {"navigate": {"risk_threshold": "low", "decision": "deny"}},
            }
        ]
    }
    with open(path, "w") as f:
        f.write(yaml.dump(data))
    engine.load_policy_file(path)
    p = engine.get_policy("dict_rules_policy")
    assert p is not None
    assert len(p.rules) == 1
    assert p.rules[0].action_type == "navigate"


def test_load_policy_file_invalid(tmp_path, caplog):
    caplog.set_level("WARNING")
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    invalid_file = tmp_path / "bad.yaml"
    invalid_file.write_text("{invalid: yaml: [")
    count = engine.load_policies_from_dir()
    assert count == 0
    assert "Failed to load policy" in caplog.text


def test_reload_policies_no_dir():
    engine = PolicyEngine()
    count = engine.reload_policies()
    assert count == 0


def test_reload_policies_with_dir(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    policy_file = tmp_path / "reload.yaml"
    policy_file.write_text(yaml.dump({"policies": [{"name": "reloaded"}]}))
    count = engine.reload_policies()
    assert count == 1
    assert engine.get_policy("reloaded") is not None
    assert engine.get_policy("default") is not None


def test_evaluate_domain_blocked():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.gov/test"})
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.DENY


def test_evaluate_domain_allowed():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com/test"})
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.ALLOW


def test_evaluate_domain_action_limit():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="limit_test",
        domain_rules=[DomainRule(pattern="*.example.com", allow=True, max_actions=1)],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT, params={"url": "https://sub.example.com/page"})
    decision = engine.evaluate(req, session_id="s1")
    assert decision == PolicyDecision.ALLOW
    decision = engine.evaluate(req, session_id="s1")
    assert decision == PolicyDecision.DENY


def test_evaluate_domain_requires_confirmation():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="confirm_test",
        domain_rules=[DomainRule(pattern="*.example.com", allow=True, require_confirmation_for=["screenshot"])],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT, params={"url": "https://www.example.com/page"})
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.REQUIRE_CONFIRMATION


def test_evaluate_rate_limit_exceeded():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="rate_test",
        rate_limit=RateLimitRule(max_actions_per_minute=0, max_actions_per_session=1),
    ))
    engine._rate_limiter.record_action("s1")
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req, session_id="s1")
    assert decision == PolicyDecision.DENY


def test_evaluate_no_matching_rules():
    engine = PolicyEngine()
    engine._policies.clear()
    engine.add_policy(Policy(
        name="empty",
        default_decision=PolicyDecision.ALLOW,
        rules=[],
        domain_rules=[],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.ALLOW


def test_evaluate_disabled_policy():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="disabled_test",
        enabled=False,
        rules=[PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.DENY)],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.ALLOW


def test_evaluate_high_priority_decision():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="priority_test",
        rules=[
            PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.ALLOW, priority=10),
            PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.DENY, priority=20),
        ],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.DENY


def test_check_deny_raises():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "alert(1)"})
    with pytest.raises(SafetyBlocked):
        engine.check(req)


def test_check_requires_confirmation_denied():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.DESKTOP_CLICK)
    with patch.object(engine, '_confirm_action', return_value=False):
        with pytest.raises(SafetyBlocked, match="requires human confirmation"):
            engine.check(req, session_id="s1")


def test_check_requires_confirmation_allowed():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.DESKTOP_CLICK)
    with patch.object(engine, '_confirm_action', return_value=True):
        engine.check(req, session_id="s1")


def test_check_records_action_with_session():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    engine.check(req, session_id="s1")
    assert len(engine._rate_limiter._action_timestamps.get("s1", [])) == 1


def test_check_no_session_does_not_record():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    engine.check(req)
    assert "no_session" not in engine._rate_limiter._action_timestamps


def test_check_audit_logged():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    engine.check(req)
    assert len(engine._audit_log) == 1


def test_confirm_action_yes():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE)
    with patch("sys.stdin.readline", return_value="y\n"):
        assert engine._confirm_action(req) is True


def test_confirm_action_no():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE)
    with patch("sys.stdin.readline", return_value="n\n"):
        assert engine._confirm_action(req) is False


def test_confirm_action_eof():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE)
    with patch("sys.stdin.readline", side_effect=EOFError()):
        assert engine._confirm_action(req) is False


def test_get_decision_for_action_full():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    info = engine.get_decision_for_action(req, session_id="s1")
    assert "timestamp" in info
    assert info["action_type"] == "navigate"
    assert info["risk_level"] in ("low", "medium", "high", "critical")


def test_make_safety_hook():
    engine = PolicyEngine()
    hook = engine.make_safety_hook(session_id="test_session")
    import asyncio
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    asyncio.run(hook(req))


def test_extract_domain():
    engine = PolicyEngine()
    assert engine._extract_domain("https://www.example.com/path") == "www.example.com"
    assert engine._extract_domain("http://example.com:8080/path") == "example.com"
    assert engine._extract_domain("no-protocol") == ""


def test_domain_matches():
    engine = PolicyEngine()
    assert engine._domain_matches("*.gov", "example.gov") is True
    assert engine._domain_matches("*.gov", "example.com") is False
    assert engine._domain_matches("*", "anything.com") is True
    assert engine._domain_matches("example.com", "example.com") is True
    assert engine._domain_matches("example.com", "other.com") is False


def test_risk_threshold_value():
    assert PolicyEngine._risk_threshold_value("low") == 0.1
    assert PolicyEngine._risk_threshold_value("medium") == 0.4
    assert PolicyEngine._risk_threshold_value("high") == 0.7
    assert PolicyEngine._risk_threshold_value("critical") == 0.9
    assert PolicyEngine._risk_threshold_value("unknown") == 0.7


def test_audit_log_truncation():
    engine = PolicyEngine()
    engine._max_audit_entries = 5
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    for _ in range(10):
        engine.check(req)
    assert len(engine._audit_log) == 5


def test_evaluate_with_risk_score_thresholds():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="risk_test",
        rules=[
            PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.DENY),
        ],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.DENY


def test_evaluate_log_decision():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="log_test",
        rules=[
            PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.LOG),
        ],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.LOG


def test_set_policy_dir_with_yaml_load(tmp_path):
    engine = PolicyEngine()
    d = tmp_path / "policies"
    d.mkdir()
    policy_file = d / "custom.yaml"
    data = {"policies": [{"name": "dir_loaded", "rules": [{"action_type": "navigate", "risk_threshold": "low", "decision": "deny"}]}]}
    policy_file.write_text(yaml.dump(data))
    engine.set_policy_dir(str(d))
    assert engine.get_policy("dir_loaded") is not None


def test_load_policy_file_full_flow(tmp_path):
    engine = PolicyEngine()
    path = str(tmp_path / "full.yaml")
    data = {
        "policies": [
            {
                "name": "full_policy",
                "description": "Full test",
                "version": "3.0",
                "rules": [
                    {"action_type": "click", "risk_threshold": "medium", "decision": "deny", "reasons": ["Testing"]},
                ],
                "domain_rules": [
                    {"pattern": "*.test.com", "allow": False, "max_actions": 5, "require_confirmation_for": ["screenshot"], "reasons": ["Test domain"]},
                ],
                "rate_limit": {"max_actions_per_minute": 20, "max_actions_per_session": 100, "cooldown_seconds": 30},
                "default_decision": "require_confirmation",
                "enabled": True,
            }
        ]
    }
    with open(path, "w") as f:
        yaml.dump(data, f)
    engine.load_policy_file(path)
    p = engine.get_policy("full_policy")
    assert p is not None
    assert p.description == "Full test"
    assert p.version == "3.0"
    assert len(p.rules) == 1
    assert p.rules[0].reasons == ["Testing"]
    assert len(p.domain_rules) == 1
    assert p.domain_rules[0].max_actions == 5
    assert p.domain_rules[0].require_confirmation_for == ["screenshot"]
    assert p.rate_limit is not None
    assert p.rate_limit.cooldown_seconds == 30
    assert p.default_decision == PolicyDecision.REQUIRE_CONFIRMATION
    assert p.enabled is True


def test_load_policy_file_yml_extension(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    policy_file = tmp_path / "test.yml"
    data = {"policies": [{"name": "yml_policy"}]}
    policy_file.write_text(yaml.dump(data))
    count = engine.load_policies_from_dir()
    assert count == 1
    assert engine.get_policy("yml_policy") is not None


def test_reload_policies_resets_and_reloads(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    custom_file = tmp_path / "reload_test.yaml"
    custom_file.write_text(yaml.dump({"policies": [{"name": "reload_custom"}]}))
    count = engine.reload_policies()
    assert count == 1
    assert engine.get_policy("reload_custom") is not None
    assert engine.get_policy("default") is not None


def test_evaluate_multiple_policies():
    engine = PolicyEngine()
    engine.add_policy(Policy(
        name="high_priority_deny",
        rules=[PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.DENY, priority=100)],
    ))
    engine.add_policy(Policy(
        name="low_priority_allow",
        rules=[PolicyRule(action_type="screenshot", risk_threshold="low", decision=PolicyDecision.ALLOW, priority=10)],
    ))
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.DENY


def test_evaluate_no_domain_no_url():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.SCREENSHOT)
    decision = engine.evaluate(req)
    assert decision == PolicyDecision.ALLOW


def test_check_deny_domain_raises():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://www.gov/page"})
    with pytest.raises(SafetyBlocked):
        engine.check(req)


def test_check_require_confirmation_custom():
    engine = PolicyEngine()
    req = ActionRequest(type=ActionType.DESKTOP_CLICK)
    with patch.object(engine, '_confirm_action', return_value=True):
        engine.check(req, session_id="custom_session")
    assert "custom_session" in engine._rate_limiter._action_timestamps


def test_make_safety_hook_blocked():
    engine = PolicyEngine()
    hook = engine.make_safety_hook("test_session")
    import asyncio
    req = ActionRequest(type=ActionType.EVALUATE, params={"script": "bad()"})
    with pytest.raises(SafetyBlocked):
        asyncio.run(hook(req))


def test_set_policy_dir_exists_empty(tmp_path):
    engine = PolicyEngine()
    d = tmp_path / "empty_policies"
    d.mkdir()
    engine.set_policy_dir(str(d))
    assert engine._policy_dir == d


def test_load_policies_from_dir_no_yaml(tmp_path):
    engine = PolicyEngine()
    engine._policy_dir = tmp_path
    not_yaml = tmp_path / "readme.txt"
    not_yaml.write_text("not a policy file")
    count = engine.load_policies_from_dir()
    assert count == 0


def test_rate_limiter_check_zero_limits():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=0, max_actions_per_session=0)
    limiter.check("s1", rule)
    limiter.record_action("s1")
    limiter.check("s1", rule)


def test_rate_limiter_session_limit_zero():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=100, max_actions_per_session=0)
    limiter.check("s1", rule)
    limiter.record_action("s1")
    limiter.check("s1", rule)


def test_rate_limiter_multiple_sessions():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=100, max_actions_per_session=1)
    limiter.check("s1", rule)
    limiter.check("s2", rule)
    limiter.record_action("s1")
    limiter.record_action("s2")
    with pytest.raises(SafetyBlocked, match="Session action limit exceeded"):
        limiter.check("s1", rule)
    with pytest.raises(SafetyBlocked, match="Session action limit exceeded"):
        limiter.check("s2", rule)


def test_rate_limiter_per_minute_exact_limit():
    limiter = RateLimiter()
    rule = RateLimitRule(max_actions_per_minute=3, max_actions_per_session=100)
    limiter.record_action("s1")
    limiter.record_action("s1")
    limiter.record_action("s1")
    with pytest.raises(SafetyBlocked, match="Rate limit exceeded"):
        limiter.check("s1", rule)
