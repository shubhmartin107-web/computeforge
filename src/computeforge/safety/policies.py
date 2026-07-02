from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from computeforge.core.actions import ActionRequest
from computeforge.core.exceptions import SafetyBlocked
from computeforge.safety.risk import RiskScorer

logger = logging.getLogger("computeforge.safety.policies")


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    LOG = "log"


@dataclass
class DomainRule:
    """Rule for a specific domain pattern."""
    pattern: str = "*"
    allow: bool = True
    max_actions: int = 0
    require_confirmation_for: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class RateLimitRule:
    """Rate limiting configuration."""
    max_actions_per_minute: int = 30
    max_actions_per_session: int = 200
    cooldown_seconds: int = 0


@dataclass
class PolicyRule:
    """A single policy rule with full context."""
    action_type: str = "*"
    risk_threshold: str = "high"
    decision: PolicyDecision = PolicyDecision.ALLOW
    domains: list[str] | None = None
    reasons: list[str] = field(default_factory=list)
    priority: int = 10


@dataclass
class Policy:
    """A comprehensive named policy."""
    name: str = "default"
    description: str = ""
    version: str = "1.0"
    rules: list[PolicyRule] = field(default_factory=list)
    domain_rules: list[DomainRule] = field(default_factory=list)
    rate_limit: RateLimitRule | None = None
    default_decision: PolicyDecision = PolicyDecision.ALLOW
    enabled: bool = True


class RateLimiter:
    """Tracks and enforces rate limits for actions."""

    def __init__(self):
        self._action_timestamps: dict[str, list[datetime]] = {}
        self._session_action_counts: dict[str, int] = {}

    def check(self, session_id: str, rate_limit: RateLimitRule | None) -> None:
        if rate_limit is None:
            return

        now = datetime.utcnow()

        # Per-minute rate
        if rate_limit.max_actions_per_minute > 0:
            timestamps = self._action_timestamps.get(session_id, [])
            cutoff = now - timedelta(minutes=1)
            recent = [t for t in timestamps if t > cutoff]
            if len(recent) >= rate_limit.max_actions_per_minute:
                raise SafetyBlocked(
                    "rate_limit",
                    f"Rate limit exceeded: {rate_limit.max_actions_per_minute} actions per minute",
                )
            self._action_timestamps[session_id] = recent

        # Per-session total
        count = self._session_action_counts.get(session_id, 0)
        if rate_limit.max_actions_per_session > 0 and count >= rate_limit.max_actions_per_session:
            raise SafetyBlocked(
                "session_limit",
                f"Session action limit exceeded: {rate_limit.max_actions_per_session}",
            )

    def record_action(self, session_id: str) -> None:
        timestamps = self._action_timestamps.get(session_id, [])
        timestamps.append(datetime.utcnow())
        self._action_timestamps[session_id] = timestamps
        self._session_action_counts[session_id] = self._session_action_counts.get(session_id, 0) + 1

    def reset(self, session_id: str) -> None:
        self._action_timestamps.pop(session_id, None)
        self._session_action_counts.pop(session_id, None)


class PolicyEngine:
    """Comprehensive policy engine with domain rules, rate limiting, and audit logging.

    Features:
    - YAML-based policy definitions
    - Multi-factor policy evaluation (rules + domains + rate limits)
    - Domain pattern matching with wildcards
    - Per-session rate limiting
    - Detailed audit trail
    - Policy hot-reloading
    """

    def __init__(self, risk_scorer: RiskScorer | None = None):
        self._risk_scorer = risk_scorer or RiskScorer()
        self._policies: dict[str, Policy] = {}
        self._rate_limiter = RateLimiter()
        self._audit_log: list[dict[str, Any]] = []
        self._max_audit_entries = 1000
        self._policy_dir: Path | None = None
        self._load_default_policy()

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    # ─── Policy Management ────────────────────────────────────────────

    def _load_default_policy(self) -> None:
        default = Policy(
            name="default",
            description="Default safety policy for ComputeForge",
            version="1.0",
            rules=[
                PolicyRule(action_type="evaluate", risk_threshold="medium", decision=PolicyDecision.DENY, priority=100, reasons=["JavaScript execution restricted by default policy"]),
                PolicyRule(action_type="desktop_click", risk_threshold="medium", decision=PolicyDecision.REQUIRE_CONFIRMATION, priority=90, reasons=["Desktop clicks require human confirmation"]),
                PolicyRule(action_type="desktop_type", risk_threshold="medium", decision=PolicyDecision.REQUIRE_CONFIRMATION, priority=90, reasons=["Desktop typing requires human confirmation"]),
                PolicyRule(action_type="desktop_keypress", risk_threshold="medium", decision=PolicyDecision.REQUIRE_CONFIRMATION, priority=90, reasons=["Desktop keypress requires human confirmation"]),
                PolicyRule(action_type="desktop_screenshot", risk_threshold="high", decision=PolicyDecision.REQUIRE_CONFIRMATION, priority=80, reasons=["Desktop screenshots may capture sensitive information"]),
                PolicyRule(action_type="navigate", risk_threshold="critical", decision=PolicyDecision.DENY, priority=70, reasons=["Navigation to critical-risk URLs blocked"]),
            ],
            domain_rules=[
                DomainRule(pattern="*.gov", allow=False, reasons=["Government sites blocked by default"]),
                DomainRule(pattern="*.mil", allow=False, reasons=["Military sites blocked by default"]),
            ],
            rate_limit=RateLimitRule(max_actions_per_minute=30, max_actions_per_session=200),
        )
        self._policies[default.name] = default

    def set_policy_dir(self, path: str | Path) -> None:
        self._policy_dir = Path(path)
        if self._policy_dir.exists():
            self.load_policies_from_dir()

    def load_policies_from_dir(self) -> int:
        if not self._policy_dir or not self._policy_dir.exists():
            return 0
        count = 0
        for f in sorted(self._policy_dir.glob("*.yaml")) + sorted(self._policy_dir.glob("*.yml")):
            try:
                self.load_policy_file(str(f))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load policy {f}: {e}")
        return count

    def load_policy_file(self, path: str) -> None:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not data:
            return
        for policy_data in data.get("policies", []):
            rules_data = policy_data.get("rules", [])
            # Handle both list of dicts and dict of rules
            if isinstance(rules_data, dict):
                rules = [PolicyRule(action_type=k, **v) for k, v in rules_data.items()]
            else:
                rules = [PolicyRule(**rule) for rule in rules_data]
            policy = Policy(
                name=policy_data.get("name", "unnamed"),
                description=policy_data.get("description", ""),
                version=policy_data.get("version", "1.0"),
                rules=rules,
                domain_rules=[DomainRule(**dr) for dr in policy_data.get("domain_rules", [])],
                rate_limit=RateLimitRule(**policy_data.get("rate_limit", {})) if policy_data.get("rate_limit") else None,
                default_decision=PolicyDecision(policy_data.get("default_decision", "allow")),
                enabled=policy_data.get("enabled", True),
            )
            self._policies[policy.name] = policy
            logger.info(f"Loaded policy: {policy.name} v{policy.version} ({len(policy.rules)} rules)")

    def add_policy(self, policy: Policy) -> None:
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Policy | None:
        return self._policies.get(name)

    def remove_policy(self, name: str) -> None:
        self._policies.pop(name, None)

    def list_policies(self) -> list[Policy]:
        return list(self._policies.values())

    def reload_policies(self) -> int:
        if self._policy_dir:
            self._load_default_policy()
            return self.load_policies_from_dir()
        return 0

    # ─── Evaluation ──────────────────────────────────────────────────

    def evaluate(self, request: ActionRequest, session_id: str | None = None) -> PolicyDecision:
        """Evaluate an action against all policies with full context."""
        action_type_str = request.type.value if hasattr(request.type, "value") else str(request.type)
        _, risk_score, risk_reason = self._risk_scorer.assess(request)

        url = request.params.get("url", "")
        domain = self._extract_domain(url)

        decisions: list[tuple[PolicyDecision, int, str]] = []

        for policy in self._policies.values():
            if not policy.enabled:
                continue

            # Check domain rules
            if domain:
                for dr in policy.domain_rules:
                    if self._domain_matches(dr.pattern, domain):
                        if not dr.allow:
                            decisions.append((PolicyDecision.DENY, 200, f"Domain blocked by policy: {dr.pattern}"))
                        if dr.max_actions > 0:
                            domain_key = f"{session_id}:{domain}" if session_id else domain
                            count = getattr(self, "_domain_counts", {}).get(domain_key, 0)
                            if count >= dr.max_actions:
                                decisions.append((PolicyDecision.DENY, 190, f"Domain action limit exceeded: {domain}"))
                            self._domain_counts = {**getattr(self, "_domain_counts", {}), domain_key: count + 1}
                        if dr.require_confirmation_for and action_type_str in dr.require_confirmation_for:
                            decisions.append((PolicyDecision.REQUIRE_CONFIRMATION, 150, f"Domain requires confirmation for {action_type_str}"))

            # Check rate limits
            if session_id and policy.rate_limit:
                try:
                    self._rate_limiter.check(session_id, policy.rate_limit)
                except SafetyBlocked as e:
                    decisions.append((PolicyDecision.DENY, 180, str(e)))

            # Check rules
            for rule in policy.rules:
                if rule.action_type != "*" and rule.action_type != action_type_str:
                    continue
                threshold_value = self._risk_threshold_value(rule.risk_threshold)
                if risk_score >= threshold_value:
                    reason = "; ".join(rule.reasons) if rule.reasons else risk_reason
                    decisions.append((rule.decision, rule.priority, reason))

        # Sort by priority (higher = more specific)
        decisions.sort(key=lambda d: d[1], reverse=True)

        if decisions:
            return decisions[0][0]

        return PolicyDecision.ALLOW

    def check(self, request: ActionRequest, session_id: str | None = None) -> None:
        """Check if an action is allowed; raises SafetyBlocked if not."""
        decision = self.evaluate(request, session_id)
        action_type_str = request.type.value if hasattr(request.type, "value") else str(request.type)
        self._audit(action_type_str, request.params, decision.value, session_id)

        if decision == PolicyDecision.DENY:
            raise SafetyBlocked(action_type=action_type_str, reason="Blocked by safety policy", policy="default")

        if decision == PolicyDecision.REQUIRE_CONFIRMATION:
            if not self._confirm_action(request):
                raise SafetyBlocked(action_type=action_type_str, reason="Action requires human confirmation", policy="default")

        if session_id:
            self._rate_limiter.record_action(session_id)

    def _confirm_action(self, request: ActionRequest) -> bool:
        """Prompt for human confirmation of an action."""
        import sys
        action_str = f"{request.type.value}({request.params})" if hasattr(request.type, "value") else str(request)
        print(f"\n⚠️  ACTION REQUIRES CONFIRMATION: {action_str}")
        print("    Allow this action? [y/N] ", end="", flush=True)
        try:
            answer = sys.stdin.readline().strip().lower()
            return answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def get_decision_for_action(self, request: ActionRequest, session_id: str | None = None) -> dict[str, Any]:
        action_type_str = request.type.value if hasattr(request.type, "value") else str(request.type)
        risk_level, risk_score, risk_reason = self._risk_scorer.assess(request)
        decision = self.evaluate(request, session_id)

        return {
            "action_type": action_type_str,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level.value,
            "risk_reason": risk_reason,
            "decision": decision.value,
            "allowed": decision == PolicyDecision.ALLOW,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ─── Audit ────────────────────────────────────────────────────────

    def _audit(self, action_type: str, params: dict[str, Any], decision: str, session_id: str | None = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type,
            "params": params,
            "decision": decision,
            "session_id": session_id,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._audit_log[-limit:]

    def clear_audit_log(self) -> None:
        self._audit_log.clear()

    # ─── Helpers ──────────────────────────────────────────────────────

    def _extract_domain(self, url: str) -> str:
        """Extract domain from a URL."""
        match = re.search(r"://([^/]+)", url)
        if match:
            domain = match.group(1)
            return domain.split(":")[0]  # Remove port
        return ""

    def _domain_matches(self, pattern: str, domain: str) -> bool:
        """Check if a domain matches a pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern.startswith("*."):
            return domain.endswith(pattern[1:])
        return domain == pattern

    def make_safety_hook(self, session_id: str | None = None):
        engine = self

        async def safety_hook(request: ActionRequest) -> None:
            engine.check(request, session_id)

        return safety_hook

    @staticmethod
    def _risk_threshold_value(threshold: str) -> float:
        mapping = {"low": 0.1, "medium": 0.4, "high": 0.7, "critical": 0.9}
        return mapping.get(threshold, 0.7)
