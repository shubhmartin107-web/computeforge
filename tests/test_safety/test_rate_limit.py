"""Tests for rate limiting."""

import pytest

from computeforge.core.exceptions import SafetyBlocked
from computeforge.safety.policies import RateLimiter, RateLimitRule


class TestRateLimiter:
    def test_no_rate_limit(self):
        limiter = RateLimiter()
        limiter.check("session-1", None)

    def test_rate_limit_under(self):
        limiter = RateLimiter()
        rule = RateLimitRule(max_actions_per_minute=10, max_actions_per_session=100)
        for _ in range(5):
            limiter.check("session-1", rule)
            limiter.record_action("session-1")

    def test_rate_limit_exceeded_per_session(self):
        limiter = RateLimiter()
        rule = RateLimitRule(max_actions_per_minute=100, max_actions_per_session=3)
        for _ in range(3):
            limiter.check("session-2", rule)
            limiter.record_action("session-2")
        with pytest.raises(SafetyBlocked, match="session"):
            limiter.check("session-2", rule)

    def test_rate_limit_reset(self):
        limiter = RateLimiter()
        rule = RateLimitRule(max_actions_per_minute=100, max_actions_per_session=3)
        for _ in range(3):
            limiter.check("session-3", rule)
            limiter.record_action("session-3")
        limiter.reset("session-3")
        limiter.check("session-3", rule)  # Should not raise
