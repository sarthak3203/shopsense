"""
tests/test_m7_reliability.py
Tests the reliability layer in isolation -- no LangGraph, no LLM calls.
"""

import pytest

from src.reliability import (
    BackendUnavailableError,
    CircuitBreaker,
    CircuitState,
    TransientBackendError,
    reset_all_breakers,
    resilient_call,
)


@pytest.fixture(autouse=True)
def _reset_breakers():
    reset_all_breakers()
    yield
    reset_all_breakers()


def test_resilient_call_succeeds_on_clean_function():
    result = resilient_call("test_clean", lambda: {"found": True, "value": 42})
    assert result == {"found": True, "value": 42}


def test_resilient_call_retries_and_recovers():
    """Fails twice with TransientBackendError, succeeds on 3rd attempt --
    should succeed overall because tenacity retries up to 3 attempts."""
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TransientBackendError("simulated flake")
        return {"found": True}

    result = resilient_call("test_flaky_recovers", flaky)
    assert result == {"found": True}
    assert attempts["count"] == 3


def test_resilient_call_raises_backend_unavailable_after_exhausting_retries():
    def always_fails():
        raise TransientBackendError("always down")

    with pytest.raises(BackendUnavailableError):
        resilient_call("test_always_fails", always_fails)


def test_circuit_breaker_trips_after_threshold():
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)
    assert breaker.state == CircuitState.CLOSED

    for _ in range(3):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_call() is False


def test_circuit_breaker_half_opens_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    import time
    time.sleep(0.02)

    assert breaker.allow_call() is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_recovers_to_closed_on_success():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
    breaker.record_failure()
    import time
    time.sleep(0.02)
    breaker.allow_call()  # moves to HALF_OPEN
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


def test_resilient_call_short_circuits_when_breaker_open():
    def always_fails():
        raise TransientBackendError("down")

    # Trip the breaker via repeated resilient_call failures
    for _ in range(2):
        with pytest.raises(BackendUnavailableError):
            resilient_call("test_trip_via_calls", always_fails)

    # Breaker should now be OPEN (threshold default is 3, but each
    # resilient_call that exhausts retries counts as 1 failure to the
    # breaker -- 2 calls with default threshold=3 may not trip yet,
    # so trip explicitly to make the assertion deterministic)
    from src.reliability import _get_breaker
    breaker = _get_breaker("test_trip_via_calls")
    breaker._state = CircuitState.OPEN
    breaker._opened_at = __import__("time").monotonic()

    call_count = {"n": 0}

    def should_not_be_called():
        call_count["n"] += 1
        raise TransientBackendError("down")

    with pytest.raises(BackendUnavailableError, match="Circuit breaker OPEN"):
        resilient_call("test_trip_via_calls", should_not_be_called)

    assert call_count["n"] == 0  # never actually invoked -- short-circuited