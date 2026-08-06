import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.order_actions_agent import run_agent


def test_shipping_status_query():
    result = run_agent("What's the shipping status of order ORD-1187?")
    print("\nANSWER:", result["final_answer"])
    print("TOOLS CALLED:", [t["name"] for t in result["tool_calls_made"]])
    tool_names = [t["name"] for t in result["tool_calls_made"]]
    assert "get_shipping_status" in tool_names or "order_lookup" in tool_names


def test_refund_calculation_query():
    result = run_agent("How much refund is order ORD-8842 eligible for?")
    print("\nANSWER:", result["final_answer"])
    print("TOOLS CALLED:", [t["name"] for t in result["tool_calls_made"]])
    tool_names = [t["name"] for t in result["tool_calls_made"]]
    assert "calculate_refund_amount" in tool_names


def test_nonexistent_order_handled_gracefully():
    result = run_agent("What's the status of order ORD-0000?")
    print("\nANSWER:", result["final_answer"])
    print("TOOLS CALLED:", [t["name"] for t in result["tool_calls_made"]])
    # The tool result should reflect "not found" — check it made it into the trace
    assert any(
        r["result"].get("found") is False
        for r in result["tool_calls_made"]
    )


def test_full_refund_execution_flow():
    result = run_agent(
        "Order ORD-5521 arrived defective and the customer wants a refund. "
        "Check eligibility and process it if eligible."
    )
    print("\nANSWER:", result["final_answer"])
    print("TOOLS CALLED:", [t["name"] for t in result["tool_calls_made"]])
    tool_names = [t["name"] for t in result["tool_calls_made"]]
    assert "calculate_refund_amount" in tool_names