"""
src/order_system_client.py
Resilience layer wrapping M2's src/mock_apis.py functions.

Kept as a separate module (not edited into mock_apis.py) for the same reason
M6 extracted escalation_reviewer_agent.py: mock_apis.py stays pure tool
mechanics, this module owns retry/circuit-breaker/fallback concerns.

FLAKY_MODE (env var, default "off"): when "on", each wrapped call has a
random chance of raising TransientBackendError before delegating to the
real mock_apis function -- lets us actually exercise retries and the
circuit breaker in tests/demos without needing a real flaky backend.
"""

import os
import random

from src.mock_apis import (
    calculate_refund_amount as _calculate_refund_amount,
    get_shipping_status as _get_shipping_status,
    initiate_refund_or_replacement as _initiate_refund_or_replacement,
    order_lookup as _order_lookup,
)
from src.reliability import (
    BackendUnavailableError,
    TransientBackendError,
    resilient_call,
)

__all__ = [
    "order_lookup",
    "get_shipping_status",
    "calculate_refund_amount",
    "initiate_refund_or_replacement",
    "BackendUnavailableError",
]

_FLAKY_MODE = os.environ.get("FLAKY_MODE", "off").lower() == "on"
_FLAKY_FAILURE_RATE = float(os.environ.get("FLAKY_FAILURE_RATE", "0.5"))


def _maybe_inject_failure(backend_name: str) -> None:
    if _FLAKY_MODE and random.random() < _FLAKY_FAILURE_RATE:
        raise TransientBackendError(f"Injected transient failure for {backend_name}")


def order_lookup(order_id: str) -> dict:
    def call():
        _maybe_inject_failure("order_lookup")
        return _order_lookup(order_id)

    return resilient_call("order_lookup", call)


def get_shipping_status(order_id: str) -> dict:
    def call():
        _maybe_inject_failure("get_shipping_status")
        return _get_shipping_status(order_id)

    return resilient_call("get_shipping_status", call)


def calculate_refund_amount(order_id: str) -> dict:
    def call():
        _maybe_inject_failure("calculate_refund_amount")
        return _calculate_refund_amount(order_id)

    return resilient_call("calculate_refund_amount", call)


def initiate_refund_or_replacement(order_id: str, action: str, amount: float = None) -> dict:
    def call():
        _maybe_inject_failure("initiate_refund_or_replacement")
        return _initiate_refund_or_replacement(order_id, action, amount)

    return resilient_call("initiate_refund_or_replacement", call)