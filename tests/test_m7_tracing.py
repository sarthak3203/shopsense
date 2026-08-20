"""
tests/test_m7_tracing.py
Confirms @observe() and trace_ticket_session don't alter function behavior
or crash, whether or not Langfuse keys are configured. Does NOT assert
anything about what actually reaches the Langfuse server -- that's outside
the scope of a fast local test suite. Use the Langfuse UI to manually
confirm a real trace appears (see M7 Step 9 in the build doc).
"""

from src.tracing import observe, trace_ticket_session


def test_observe_decorator_preserves_return_value():
    @observe(name="test_fn")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_observe_decorator_preserves_exceptions():
    @observe(name="test_fn_raises")
    def boom():
        raise ValueError("expected")

    import pytest
    with pytest.raises(ValueError, match="expected"):
        boom()


def test_trace_ticket_session_context_manager_does_not_raise():
    with trace_ticket_session(customer_id="CUST-1", ticket_id="TICK-1", issue_type="refund_request"):
        pass  # just confirming no exception, even with no/invalid keys configured