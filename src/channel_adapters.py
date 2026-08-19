import asyncio
from fastmcp import Client
from src.mcp_server import mcp


async def _call_tool(tool_name: str, args: dict) -> dict:
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, args)
        return result.data


async def chat_channel_order_lookup(order_id: str) -> dict:
    data = await _call_tool("order_lookup_tool", {"order_id": order_id})
    print(f"[CHAT] order_lookup_tool({order_id}) -> {data}")
    return data


async def email_channel_order_lookup(order_id: str) -> dict:
    data = await _call_tool("order_lookup_tool", {"order_id": order_id})
    print(f"[EMAIL] order_lookup_tool({order_id}) -> {data}")
    return data


async def main():
    await chat_channel_order_lookup("ORD-8842")
    await email_channel_order_lookup("ORD-8842")


if __name__ == "__main__":
    asyncio.run(main())