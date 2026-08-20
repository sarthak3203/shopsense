"""
src/reliability.py
Reliability hardening for calls to the (mocked) order-system backend.

Two layers, applied together via the `resilient_call` helper:

1. Retries (tenacity): transient-failure tolerance. Exponential backoff,
   max 3 attempts, only retries on our injected TransientBackendError --
   never retries a clean domain result like {"found": False}, since that's
   not a failure, it's a valid answer.

2. Circuit breaker (hand-rolled, no third-party lib -- see M7 design notes):
   after N consecutive failures for a given backend function, the breaker
   trips OPEN and short-circuits further calls for a cooldown window,
   instead of hammering an already-struggling backend. After the cooldown
   it allows one HALF_OPEN trial call to test recovery.

If retries are exhausted OR the breaker is OPEN, resilient_call raises
BackendUnavailableError instead of letting the raw exception propagate --
callers (LangGraph nodes) catch that specific exception and route to
human escalation rather than crashing the ticket pipeline.
"""

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


class TransientBackendError(Exception):
    """Raised by mock_apis.py to simulate a flaky backend call failing."""


class BackendUnavailableError(Exception):
    """
    Raised by resilient_call when retries are exhausted or the circuit
    breaker is OPEN. Callers should catch this and escalate to a human,
    never silently swallow it.
    """


class CircuitState(Enum):
    CLOSED = "closed"        # normal operation
    OPEN = "open"             # tripped -- rejecting calls
    HALF_OPEN = "half_open"   # cooldown elapsed -- allow one trial call


@dataclass
class CircuitBreaker:
    """
    Simple thread-safe circuit breaker, one instance per protected function.

    failure_threshold: consecutive failures before tripping to OPEN
    cooldown_seconds:  how long to stay OPEN before allowing a trial call
    """

    failure_threshold: int = 3
    cooldown_seconds: float = 30.0

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def _time(self) -> float:
        return time.monotonic()

    def allow_call(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._time() - self._opened_at >= self.cooldown_seconds:
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            # HALF_OPEN: allow exactly one trial call through
            return True

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if (
                self._state == CircuitState.HALF_OPEN
                or self._consecutive_failures >= self.failure_threshold
            ):
                self._state = CircuitState.OPEN
                self._opened_at = self._time()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state


# One breaker per protected backend function. Shared at module level so
# failures accumulate across tickets, same as they would against a real
# flaky backend -- not reset per-call or per-ticket.
_breakers: dict[str, CircuitBreaker] = {}


def _get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)
    return _breakers[name]


def _tenacity_retrying():
    return retry(
        retry=retry_if_exception_type(TransientBackendError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )


def resilient_call(backend_name: str, fn: Callable[[], T]) -> T:
    """
    Call `fn` (a zero-arg callable wrapping a mock_apis.py function) with
    retries + circuit breaker protection, identified by `backend_name`
    (e.g. "order_lookup", "calculate_refund_amount").

    Raises BackendUnavailableError if the breaker is OPEN or retries are
    exhausted -- callers must catch this and route to human escalation.
    """
    breaker = _get_breaker(backend_name)

    if not breaker.allow_call():
        raise BackendUnavailableError(
            f"Circuit breaker OPEN for '{backend_name}' -- backend considered "
            f"unavailable, routing to human."
        )

    retrying = _tenacity_retrying()
    try:
        result = retrying(fn)()
        breaker.record_success()
        return result
    except TransientBackendError as e:
        breaker.record_failure()
        raise BackendUnavailableError(
            f"'{backend_name}' failed after retries: {e}"
        ) from e


def reset_all_breakers() -> None:
    """Test helper: reset all circuit breaker state between test cases."""
    _breakers.clear()