class ComputeForgeError(Exception):
    """Base exception for all ComputeForge errors."""


class BrowserError(ComputeForgeError):
    """Raised when a browser operation fails."""


class ActionFailed(ComputeForgeError):
    """Raised when an action execution fails."""

    def __init__(self, action_type: str, reason: str, cause: Exception | None = None):
        self.action_type = action_type
        self.reason = reason
        self.cause = cause
        super().__init__(f"{action_type}: {reason}" + (f" ({cause})" if cause else ""))


class ElementNotFound(ComputeForgeError):
    """Raised when a target element cannot be located."""

    def __init__(self, selector: str, strategy: str, page_state: str | None = None):
        self.selector = selector
        self.strategy = strategy
        self.page_state = page_state
        super().__init__(f"Element not found: selector={selector!r} strategy={strategy}")


class SafetyBlocked(ComputeForgeError):
    """Raised when an action is blocked by the safety / permission layer."""

    def __init__(self, action_type: str, reason: str, policy: str | None = None):
        self.action_type = action_type
        self.reason = reason
        self.policy = policy
        super().__init__(f"Safety block: {action_type} — {reason}")


class SessionNotFound(ComputeForgeError):
    """Raised when a session ID does not exist."""


class SessionNotActive(ComputeForgeError):
    """Raised when an operation requires an active session."""


class ConfigurationError(ComputeForgeError):
    """Raised when the configuration is invalid."""


class ProviderError(ComputeForgeError):
    """Raised when an LLM provider fails."""


class PluginError(ComputeForgeError):
    """Raised when a plugin operation fails."""


class DesktopBackendError(ComputeForgeError):
    """Raised when the desktop control backend fails."""
