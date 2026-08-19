import os
import tempfile
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.langgraph_workflow import build_graph
from src.escalation_reviewer_agent import REFUND_AUTO_APPROVE_THRESHOLD
from src.mock_apis import calculate_refund_amount


def _pick_order_above_threshold():
    """Find a real mock order whose refund_amount exceeds the auto-approve
    threshold, so the test doesn't guess at mock_orders.json contents."""
    for oid in ("ORD-8842", "ORD-5521", "ORD-1187", "ORD-3399", "ORD-9002"):
        calc = calculate_refund_amount(oid)
        if calc.get("found") and calc.get("eligible") and \
           calc.get("refund_amount", 0) > REFUND_AUTO_APPROVE_THRESHOLD:
            return oid
    return None


def _pick_order_below_threshold():
    for oid in ("ORD-8842", "ORD-5521", "ORD-1187", "ORD-3399", "ORD-9002"):
        calc = calculate_refund_amount(oid)
        if calc.get("found") and calc.get("eligible") and \
           0 < calc.get("refund_amount", 0) <= REFUND_AUTO_APPROVE_THRESHOLD:
            return oid
    return None


def test_auto_resolve_low_risk_shipping_ticket():
    with SqliteSaver.from_conn_string(":memory:") as cp:
        graph = build_graph(cp)
        result = graph.invoke(
            {
                "ticket_id": "T-TEST-1",
                "channel": "chat",
                "customer_id": "CUST-1",
                "raw_text": "Where is my order ORD-8842?",
            },
            config={"configurable": {"thread_id": "T-TEST-1"}},
        )
        assert "__interrupt__" not in result
        assert result["final_status"] == "auto_resolved"


def test_high_refund_triggers_human_approval_and_resumes():
    order_id = _pick_order_above_threshold()
    assert order_id is not None, (
        "No mock order found with refund_amount above "
        f"{REFUND_AUTO_APPROVE_THRESHOLD} — check data/mock_orders.json "
        "or lower the threshold for this test environment."
    )

    with SqliteSaver.from_conn_string(":memory:") as cp:
        graph = build_graph(cp)
        config = {"configurable": {"thread_id": "T-TEST-2"}}

        result = graph.invoke(
            {
                "ticket_id": "T-TEST-2",
                "channel": "email",
                "customer_id": "CUST-2",
                "raw_text": f"I want a refund for my order {order_id}, it's defective.",
            },
            config=config,
        )
        assert "__interrupt__" in result

        resumed = graph.invoke(
            Command(resume={"approved": True, "note": "manager approved"}),
            config=config,
        )
        assert resumed["final_status"] == "human_approved"


def test_low_refund_auto_resolves():
    order_id = _pick_order_below_threshold()
    if order_id is None:
        import pytest
        pytest.skip("No mock order found below threshold to test auto-resolve path.")

    with SqliteSaver.from_conn_string(":memory:") as cp:
        graph = build_graph(cp)
        result = graph.invoke(
            {
                "ticket_id": "T-TEST-2B",
                "channel": "chat",
                "customer_id": "CUST-2B",
                "raw_text": f"I'd like a refund for order {order_id}, it's defective.",
            },
            config={"configurable": {"thread_id": "T-TEST-2B"}},
        )
        assert "__interrupt__" not in result
        assert result["final_status"] == "auto_resolved"


def test_angry_sentiment_always_escalates_even_if_low_refund():
    order_id = _pick_order_below_threshold() or "ORD-1187"
    with SqliteSaver.from_conn_string(":memory:") as cp:
        graph = build_graph(cp)
        result = graph.invoke(
            {
                "ticket_id": "T-TEST-3",
                "channel": "chat",
                "customer_id": "CUST-3",
                "raw_text": f"This is RIDICULOUS, I am furious, refund my order {order_id} NOW.",
            },
            config={"configurable": {"thread_id": "T-TEST-3"}},
        )
        assert "__interrupt__" in result


def test_checkpoint_persists_across_new_graph_instance():
    """Simulates a restart: a brand-new SqliteSaver + brand-new compiled graph,
    backed by a real file, resuming a checkpoint written by a prior instance."""
    order_id = _pick_order_above_threshold()
    assert order_id is not None, "Need an above-threshold order to force an interrupt."

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        config = {"configurable": {"thread_id": "T-RESTART"}}

        with SqliteSaver.from_conn_string(path) as cp1:
            graph1 = build_graph(cp1)
            result = graph1.invoke(
                {
                    "ticket_id": "T-RESTART",
                    "channel": "chat",
                    "customer_id": "CUST-4",
                    "raw_text": f"Refund my order {order_id}, it never arrived.",
                },
                config=config,
            )
            assert "__interrupt__" in result

        # new checkpointer, new compiled graph, same db file on disk
        with SqliteSaver.from_conn_string(path) as cp2:
            graph2 = build_graph(cp2)
            resumed = graph2.invoke(
                Command(resume={"approved": True, "note": "resumed after restart"}),
                config=config,
            )
            assert resumed["final_status"] == "human_approved"
    finally:
        os.remove(path)