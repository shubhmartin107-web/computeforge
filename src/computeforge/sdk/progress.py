from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionProgress:
    """Progress information for batch action execution."""
    total: int = 0
    current: int = 0
    current_action: str = ""
    complete: bool = False
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[ActionProgress], None | Coroutine[Any, Any, None]]
