from __future__ import annotations

import re

from computeforge.core.actions import ActionRequest
from computeforge.models.capability import RiskLevel
from computeforge.safety.permissions import CapabilityRegistry


class RiskScorer:
    """Evaluates the risk level of an action before execution."""

    def __init__(self, capability_registry: CapabilityRegistry | None = None):
        self._registry = capability_registry or CapabilityRegistry()

    def assess(self, request: ActionRequest) -> tuple[RiskLevel, float, str]:
        """Assess the risk of an action. Returns (risk_level, score, reason)."""
        action_type_str = (
            request.type.value if hasattr(request.type, "value") else str(request.type)
        )

        base_risk = self._registry.get_risk_level(action_type_str)
        score = self._risk_level_to_score(base_risk)

        reasons = [f"Base risk: {base_risk.value}"]

        if action_type_str in ("navigate",):
            url = request.params.get("url", "")
            url_risk, url_reason = self._assess_url(url)
            score = max(score, url_risk)
            if url_reason:
                reasons.append(url_reason)

        if action_type_str in ("evaluate",):
            script = request.params.get("script", "")
            script_risk, script_reason = self._assess_script(script)
            score = max(score, script_risk)
            if script_reason:
                reasons.append(script_reason)

        if action_type_str in ("desktop_click", "desktop_type", "desktop_keypress"):
            score = max(score, 0.8)

        if request.params.get("selector", "").lower() in (
            'input[type="password"]',
            'input[name="password"]',
        ):
            score = max(score, 0.7)
            reasons.append("Password field detected")

        risk_level = self._score_to_risk_level(score)
        return (risk_level, round(score, 2), "; ".join(reasons))

    def assess_url(self, url: str) -> float:
        score, _ = self._assess_url(url)
        return score

    def _assess_url(self, url: str) -> tuple[float, str]:
        score = 0.0
        reasons = []

        dangerous_patterns = [
            (r"chrome://", 0.9, "Chrome internal page"),
            (r"file://", 0.8, "Local file access"),
            (r"javascript:", 1.0, "JavaScript URL"),
            (r"data:", 0.6, "Data URL"),
            (r"about:", 0.7, "Browser internal page"),
            (r"://localhost", 0.4, "Localhost access"),
            (r"://127\.0\.0\.1", 0.4, "Localhost access"),
            (r"://192\.168\.", 0.3, "Private network"),
            (r"://10\.", 0.3, "Private network"),
            (r"://172\.(1[6-9]|2\d|3[01])", 0.3, "Private network"),
        ]

        for pattern, risk, reason in dangerous_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                score = max(score, risk)
                reasons.append(reason)

        return (score, "; ".join(reasons) if reasons else "")

    def _assess_script(self, script: str) -> tuple[float, str]:
        score = 0.6
        reasons = ["JavaScript execution"]

        dangerous_apis = [
            (r"document\.cookie", 0.2, "Cookie access"),
            (r"localStorage", 0.1, "Local storage access"),
            (r"sessionStorage", 0.1, "Session storage access"),
            (r"fetch\(", 0.2, "Network request"),
            (r"XMLHttpRequest", 0.2, "Network request"),
            (r"navigator\.sendBeacon", 0.2, "Network request"),
            (r"window\.open", 0.3, "Window open"),
            (r"document\.write", 0.2, "Document write"),
            (r"innerHTML\s*=", 0.1, "DOM injection"),
            (r"outerHTML\s*=", 0.1, "DOM injection"),
            (r"eval\s*\(", 0.3, "Eval usage"),
            (r"new\s+Function", 0.3, "Dynamic function"),
            (r"document\.execCommand", 0.2, "Exec command"),
            (r"file://", 0.5, "File access"),
            (r"require\(", 0.3, "Module require"),
            (r"process\.", 0.5, "Process access"),
            (r"child_process", 0.8, "Child process"),
        ]

        for pattern, add, reason in dangerous_apis:
            if re.search(pattern, script):
                score += add
                reasons.append(reason)

        score = min(score, 1.0)
        return (score, "; ".join(reasons))

    def _risk_level_to_score(self, level: RiskLevel) -> float:
        mapping = {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 0.95,
        }
        return mapping.get(level, 0.4)

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= 0.9:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
