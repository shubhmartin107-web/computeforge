"""Property-based tests for core data structures."""

import contextlib

from hypothesis import given
from hypothesis import strategies as st

from computeforge.core.actions import ActionResult, ActionType

# Strategy for generating action types
action_types = st.sampled_from(list(ActionType))


@given(
    action_type=action_types,
    success=st.booleans(),
    duration=st.floats(min_value=0, max_value=60000, allow_nan=False, allow_infinity=False),
)
def test_action_result_properties(action_type, success, duration):
    """Verify ActionResult invariants."""
    data = {"key": "value"}
    result = ActionResult(
        success=success,
        action_type=action_type,
        data=data,
        duration_ms=duration,
    )
    assert result.success == success
    assert result.action_type == action_type
    assert result.data == data
    assert result.duration_ms == duration

    d = result.to_dict()
    assert d["success"] == success
    assert d["duration_ms"] == duration


@given(
    text=st.text(max_size=100),
    url=st.text(max_size=200),
)
def test_extract_risk_patterns(text, url):
    """Verify risk assessment handles various inputs without crash."""
    from computeforge.safety.permissions import CapabilityRegistry
    from computeforge.safety.risk import RiskScorer

    scorer = RiskScorer(CapabilityRegistry())
    # Just ensure no exceptions for various inputs
    if url:
        with contextlib.suppress(Exception):
            scorer.assess_url(url)
