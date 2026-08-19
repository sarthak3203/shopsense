import pytest
from fastmcp import Client
from src.mcp_server import mcp


@pytest.mark.asyncio
async def test_tools_are_registered():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert names == {
            "order_lookup_tool",
            "shipping_status_tool",
            "calculate_refund_tool",
            "initiate_refund_tool",
        }


@pytest.mark.asyncio
async def test_order_lookup_tool_matches_direct_call():
    from src.mock_apis import order_lookup
    direct = order_lookup("ORD-8842")

    async with Client(mcp) as client:
        result = await client.call_tool("order_lookup_tool", {"order_id": "ORD-8842"})
        assert result.data == direct


@pytest.mark.asyncio
async def test_calculate_refund_tool_matches_direct_call():
    from src.mock_apis import calculate_refund_amount
    direct = calculate_refund_amount("ORD-9002")

    async with Client(mcp) as client:
        result = await client.call_tool("calculate_refund_tool", {"order_id": "ORD-9002"})
        assert result.data == direct