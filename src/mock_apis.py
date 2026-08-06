"""
M2 — Mock backend APIs the Order-Actions Agent will call as tools.
These simulate real systems: order-lookup, shipping-tracker,
refund-amount calculator, and refund/replace execution.

The refund policy here is a deliberately simple placeholder
(flat 30-day return window). Real, grounded policy lookup arrives
in M3/M4 via the Policy RAG Agent — this milestone only proves
tool-calling mechanics work.
"""

import json
import random
import string
from datetime import date, datetime
from pathlib import Path

RETURN_WINDOW_DAYS = 30  # placeholder policy, replaced by real RAG lookup later

_ORDERS_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_orders.json"


def _load_orders() -> dict:
    with open(_ORDERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def order_lookup(order_id: str) -> dict:
    """Look up an order by ID. Returns order details or a not-found error."""
    orders = _load_orders()
    order = orders.get(order_id)
    if not order:
        return {"found": False, "error": f"No order found with ID {order_id}"}
    return {"found": True, **order}


def get_shipping_status(order_id: str) -> dict:
    """Get shipping/tracking status for an order."""
    order = order_lookup(order_id)
    if not order.get("found"):
        return order
    return {
        "found": True,
        "order_id": order_id,
        "delivery_status": order["delivery_status"],
        "tracking_number": order["tracking_number"],
        "carrier": order["carrier"],
        "estimated_delivery": order["estimated_delivery"],
    }


def calculate_refund_amount(order_id: str) -> dict:
    """Calculate the refund amount this order is eligible for, using the
    placeholder 30-day return window policy."""
    order = order_lookup(order_id)
    if not order.get("found"):
        return order

    order_date = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    days_since_order = (date.today() - order_date).days

    if order["delivery_status"] != "delivered":
        return {
            "found": True,
            "order_id": order_id,
            "eligible": False,
            "reason": f"Order has not been delivered yet (status: {order['delivery_status']}); "
                      f"refunds are evaluated after delivery.",
            "refund_amount": 0.0,
        }

    if days_since_order <= RETURN_WINDOW_DAYS:
        return {
            "found": True,
            "order_id": order_id,
            "eligible": True,
            "reason": f"Delivered {days_since_order} days ago, within the "
                      f"{RETURN_WINDOW_DAYS}-day return window.",
            "refund_amount": order["price"],
        }

    return {
        "found": True,
        "order_id": order_id,
        "eligible": False,
        "reason": f"Delivered {days_since_order} days ago, outside the "
                  f"{RETURN_WINDOW_DAYS}-day return window.",
        "refund_amount": 0.0,
    }


def initiate_refund_or_replacement(order_id: str, action: str, amount: float = None) -> dict:
    """Execute a mock refund or replacement. action must be 'refund' or 'replace'."""
    order = order_lookup(order_id)
    if not order.get("found"):
        return order

    if action not in ("refund", "replace"):
        return {"found": True, "success": False, "error": "action must be 'refund' or 'replace'"}

    transaction_id = "TXN-" + "".join(random.choices(string.digits, k=8))

    if action == "refund":
        return {
            "found": True,
            "success": True,
            "action": "refund",
            "order_id": order_id,
            "amount_refunded": amount if amount is not None else order["price"],
            "transaction_id": transaction_id,
        }

    return {
        "found": True,
        "success": True,
        "action": "replace",
        "order_id": order_id,
        "replacement_item": order["item_name"],
        "transaction_id": transaction_id,
    }