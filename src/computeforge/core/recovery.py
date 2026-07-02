from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from computeforge.core.actions import ActionType


class RecoveryStrategyType(Enum):
    """Types of recovery strategies for failed actions."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CONSTANT_RETRY = "constant_retry"
    LINEAR_RETRY = "linear_retry"
    FALLBACK_SELECTOR = "fallback_selector"
    RELOAD_PAGE = "reload_page"
    WAIT_AND_RETRY = "wait_and_retry"


@dataclass
class RecoveryStrategy:
    """Configuration for how to recover from action failures."""
    type: RecoveryStrategyType = RecoveryStrategyType.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    base_delay_ms: float = 500.0
    max_delay_ms: float = 10000.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        if self.type == RecoveryStrategyType.CONSTANT_RETRY:
            delay = self.base_delay_ms / 1000.0
        elif self.type == RecoveryStrategyType.LINEAR_RETRY:
            delay = (self.base_delay_ms * (attempt + 1)) / 1000.0
        elif self.type == RecoveryStrategyType.WAIT_AND_RETRY:
            delay = self.base_delay_ms / 1000.0
        else:  # EXPONENTIAL_BACKOFF
            delay = min(self.base_delay_ms * (2 ** attempt), self.max_delay_ms) / 1000.0

        if self.jitter:
            import random
            delay *= (0.5 + random.random())
        return min(delay, self.max_delay_ms / 1000.0)


class RecoveryManager:
    """Manages recovery strategies for different action types."""

    def __init__(self):
        self._strategies: dict[ActionType, RecoveryStrategy] = {}
        self._default_strategy = RecoveryStrategy()
        self._load_defaults()

    def _load_defaults(self) -> None:
        self._strategies[ActionType.NAVIGATE] = RecoveryStrategy(
            type=RecoveryStrategyType.EXPONENTIAL_BACKOFF,
            max_retries=3,
            base_delay_ms=1000.0,
        )
        self._strategies[ActionType.CLICK] = RecoveryStrategy(
            type=RecoveryStrategyType.EXPONENTIAL_BACKOFF,
            max_retries=3,
            base_delay_ms=500.0,
        )
        self._strategies[ActionType.TYPE] = RecoveryStrategy(
            type=RecoveryStrategyType.CONSTANT_RETRY,
            max_retries=2,
            base_delay_ms=200.0,
        )
        self._strategies[ActionType.SCREENSHOT] = RecoveryStrategy(
            type=RecoveryStrategyType.CONSTANT_RETRY,
            max_retries=2,
            base_delay_ms=100.0,
        )
        self._strategies[ActionType.SCROLL] = RecoveryStrategy(
            type=RecoveryStrategyType.CONSTANT_RETRY,
            max_retries=2,
            base_delay_ms=200.0,
        )
        self._strategies[ActionType.EXTRACT_TEXT] = RecoveryStrategy(
            type=RecoveryStrategyType.WAIT_AND_RETRY,
            max_retries=2,
            base_delay_ms=500.0,
        )

    def set_strategy(self, action_type: ActionType, strategy: RecoveryStrategy) -> None:
        self._strategies[action_type] = strategy

    def get_strategy(self, action_type: ActionType) -> RecoveryStrategy:
        return self._strategies.get(action_type, self._default_strategy)

    def remove_strategy(self, action_type: ActionType) -> None:
        self._strategies.pop(action_type, None)
