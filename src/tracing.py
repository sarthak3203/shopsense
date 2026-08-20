"""
src/tracing.py
Langfuse (Python SDK v4, OTel-based) tracing setup for ShopSense.

We use the framework-agnostic @observe() decorator directly on LangGraph node
functions instead of langfuse.langchain.CallbackHandler, because that handler
is a LangChain integration and this project deliberately has no LangChain
dependency (LangGraph is used standalone).

Usage:
    from src.tracing import observe, get_langfuse_client, trace_ticket_session, traced_invoke

    @observe(name="triage_node")
    def triage_node(state: TicketState) -> TicketState:
        ...

    with trace_ticket_session(customer_id, ticket_id, issue_type):
        result = traced_invoke(graph, initial_state, config)
"""

import os
from contextlib import contextmanager

from langfuse import get_client, observe, propagate_attributes

# Re-exported so callers only need to import from src.tracing
__all__ = [
    "observe",
    "get_langfuse_client",
    "trace_ticket_session",
    "flush_traces",
    "traced_invoke",
]


def get_langfuse_client():
    """
    Returns the singleton Langfuse client. Reads LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL from the environment (.env).
    If keys are missing, get_client() returns a no-op client that silently
    drops all tracing calls -- so tracing failures never break the pipeline.
    """
    return get_client()


@contextmanager
def trace_ticket_session(customer_id: str, ticket_id: str, issue_type: str = "unknown"):
    """
    Context manager that tags every span created inside it with the
    customer_id (as session_id, so all of one customer's tickets group
    together in the Langfuse UI) and the ticket_id / issue_type as metadata.

    NOTE: this alone does NOT create a parent span/trace -- it only tags
    attributes onto whatever spans happen to run inside it. To get one
    trace per ticket (with all node spans nested underneath), the actual
    graph.invoke() call must happen inside traced_invoke() (below), which
    is what opens the parent span. Use both together:

        with trace_ticket_session(customer_id, ticket_id, issue_type):
            result = traced_invoke(graph, initial_state, config)
    """
    with propagate_attributes(
        session_id=customer_id,
        tags=[issue_type],
        metadata={"ticket_id": ticket_id},
    ):
        yield


@observe(name="ticket_resolution")
def traced_invoke(graph, payload, config):
    """
    Wraps a single graph.invoke() call (whether starting a ticket or
    resuming one via Command(resume=...)) in its own @observe() span.

    This is what makes tracing produce ONE trace per ticket with all node
    spans (triage_node, action_node, etc.) nested underneath it, instead
    of each node becoming its own separate root trace. @observe() only
    nests under whatever span is currently active when it's called --
    trace_ticket_session() alone doesn't open a span, it just tags
    attributes onto whatever runs inside it. This function is what
    actually opens the parent span that the nodes then nest under.

    Always call this instead of graph.invoke() directly, and always call
    it from inside a trace_ticket_session(...) block:

        with trace_ticket_session(customer_id, ticket_id, issue_type):
            result = traced_invoke(graph, initial_state, config)
    """
    return graph.invoke(payload, config=config)


def flush_traces() -> None:
    """
    Force-flush pending spans to Langfuse. MUST be called before a
    short-lived process (e.g. the run_workflow.py CLI) exits, since
    ingestion is batched/async and won't happen automatically on exit
    in every case.
    """
    get_client().flush()