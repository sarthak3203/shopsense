"""
M2 — Tool definitions (JSON schemas) for function-calling, plus the
dispatch table that maps a tool name to the actual mock API function.
"""

from src.mock_apis import (
    calculate_refund_amount,
    get_shipping_status,
    initiate_refund_or_replacement,
    order_lookup,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "order_lookup",
            "description": "Look up full details of an order by its order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. ORD-8842"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipping_status",
            "description": "Get shipping/tracking status and estimated delivery for an order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. ORD-8842"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_refund_amount",
            "description": "Calculate the refund amount an order is eligible for, "
                            "based on delivery status and return window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. ORD-8842"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_refund_or_replacement",
            "description": "Execute a refund or replacement for an order. "
                            "Only call this after calculating eligibility, "
                            "and only when the customer's request is clear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["refund", "replace"]},
                    "amount": {"type": "number", "description": "Refund amount, if action is refund"},
                },
                "required": ["order_id", "action"],
            },
        },
    },
]

DISPATCH = {
    "order_lookup": lambda args: order_lookup(**args),
    "get_shipping_status": lambda args: get_shipping_status(**args),
    "calculate_refund_amount": lambda args: calculate_refund_amount(**args),
    "initiate_refund_or_replacement": lambda args: initiate_refund_or_replacement(**args),
}