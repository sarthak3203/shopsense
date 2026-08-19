import sys
from fastmcp import FastMCP

from src.mock_apis import (
    order_lookup,
    get_shipping_status,
    calculate_refund_amount,
    initiate_refund_or_replacement,
)

mcp = FastMCP("shopsense-order-tools")


@mcp.tool()
def order_lookup_tool(order_id: str) -> dict:
    """Look up a ShopSense order by its order ID."""
    return order_lookup(order_id)


@mcp.tool()
def shipping_status_tool(order_id: str) -> dict:
    """Get the current shipping/tracking status for an order."""
    return get_shipping_status(order_id)


@mcp.tool()
def calculate_refund_tool(order_id: str) -> dict:
    """Calculate refund eligibility and amount for an order."""
    return calculate_refund_amount(order_id)


@mcp.tool()
def initiate_refund_tool(order_id: str, action: str, amount: float) -> dict:
    """Execute a refund or replacement. action must be 'refund' or 'replace'."""
    return initiate_refund_or_replacement(order_id=order_id, action=action, amount=amount)


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", port=8000)
    else:
        mcp.run()