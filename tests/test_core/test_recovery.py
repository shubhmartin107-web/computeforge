"""Tests for the recovery system."""

from computeforge.core.actions import ActionType
from computeforge.core.recovery import RecoveryManager, RecoveryStrategy, RecoveryStrategyType


class TestRecoveryStrategy:
    def test_exponential_backoff(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.EXPONENTIAL_BACKOFF, base_delay_ms=500.0, jitter=False)
        d1 = strategy.get_delay(0)
        d2 = strategy.get_delay(1)
        d3 = strategy.get_delay(2)
        assert d1 == 0.5
        assert d2 == 1.0
        assert d3 == 2.0

    def test_constant_retry(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.CONSTANT_RETRY, base_delay_ms=1000.0, jitter=False)
        d1 = strategy.get_delay(0)
        d2 = strategy.get_delay(5)
        assert d1 == 1.0
        assert d2 == 1.0

    def test_linear_retry(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.LINEAR_RETRY, base_delay_ms=500.0, jitter=False)
        d1 = strategy.get_delay(0)
        d2 = strategy.get_delay(1)
        d3 = strategy.get_delay(2)
        assert d1 == 0.5
        assert d2 == 1.0
        assert d3 == 1.5

    def test_max_delay(self):
        strategy = RecoveryStrategy(
            type=RecoveryStrategyType.EXPONENTIAL_BACKOFF,
            base_delay_ms=1000.0,
            max_delay_ms=3000.0,
            jitter=False,
        )
        # 1, 2, 4 -> capped at 3
        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 3.0
        assert strategy.get_delay(3) == 3.0

    def test_wait_and_retry(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.WAIT_AND_RETRY, base_delay_ms=1000.0, jitter=False)
        d0 = strategy.get_delay(0)
        d5 = strategy.get_delay(5)
        assert d0 == 1.0
        assert d5 == 1.0

    def test_jitter(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.CONSTANT_RETRY, base_delay_ms=1000.0, jitter=True)
        delays = [strategy.get_delay(0) for _ in range(10)]
        # With jitter, values should vary
        assert len(set(round(d, 2) for d in delays)) > 1

    def test_wait_and_retry(self):
        strategy = RecoveryStrategy(type=RecoveryStrategyType.WAIT_AND_RETRY, base_delay_ms=500.0, jitter=False)
        d = strategy.get_delay(0)
        assert d == 0.5


class TestRecoveryManager:
    def test_default_strategies(self):
        mgr = RecoveryManager()
        assert mgr.get_strategy(ActionType.NAVIGATE).max_retries == 3
        assert mgr.get_strategy(ActionType.CLICK).max_retries == 3
        assert mgr.get_strategy(ActionType.SCREENSHOT).max_retries == 2

    def test_set_and_get_strategy(self):
        mgr = RecoveryManager()
        strategy = RecoveryStrategy(type=RecoveryStrategyType.CONSTANT_RETRY, max_retries=5)
        mgr.set_strategy(ActionType.EVALUATE, strategy)
        retrieved = mgr.get_strategy(ActionType.EVALUATE)
        assert retrieved.max_retries == 5

    def test_remove_strategy(self):
        mgr = RecoveryManager()
        mgr.remove_strategy(ActionType.CLICK)
        # Should fall back to default
        strategy = mgr.get_strategy(ActionType.CLICK)
        assert strategy is not None

    def test_unknown_action_type(self):
        mgr = RecoveryManager()
        strategy = mgr.get_strategy(ActionType.SET_VIEWPORT)
        assert strategy is not None
        assert strategy.max_retries == 3  # default
