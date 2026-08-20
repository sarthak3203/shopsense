"""FastAPI packaging for ShopSense (M8)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command, StateSnapshot

from src.api_schemas import HealthResponse, TicketCreateRequest, TicketResponse, TicketResumeRequest
from src.langgraph_workflow import build_graph
from src.tracing import flush_traces, trace_ticket_session, traced_invoke

DB_PATH = "shopsense_checkpoints.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(title="ShopSense API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _format_from_state(snapshot: StateSnapshot, thread_id: str) -> TicketResponse:
    """Map the complete checkpointed graph state to the public API response."""
    values = snapshot.values
    response_fields = {
        "requires_human": bool(values.get("requires_human")),
        "escalation_reason": values.get("escalation_reason"),
        "refund_amount": values.get("refund_amount"),
        "proposed_action": values.get("proposed_action"),
        "issue_type": values.get("issue_type"),
        "sentiment": values.get("sentiment"),
        "urgency": values.get("urgency"),
        "suspected_prompt_injection": values.get("suspected_prompt_injection"),
        "policy_answer": values.get("policy_answer"),
        "order_id": values.get("order_id"),
    }

    if snapshot.next:
        interrupt_payload = {}
        if snapshot.tasks and snapshot.tasks[0].interrupts:
            payload = snapshot.tasks[0].interrupts[0].value
            if isinstance(payload, dict):
                interrupt_payload.update(payload)

        # The graph's interrupt intentionally stays concise. Enrich the API
        # payload from the full snapshot so a paused ticket exposes the same
        # review context as its top-level response fields.
        interrupt_payload.update({
            key: response_fields[key]
            for key in (
                "issue_type", "sentiment", "urgency", "suspected_prompt_injection",
                "proposed_action", "refund_amount", "escalation_reason", "policy_answer",
            )
        })
        return TicketResponse(
            thread_id=thread_id,
            status="paused_for_approval",
            interrupt_payload=interrupt_payload,
            **response_fields,
        )

    return TicketResponse(
        thread_id=thread_id,
        status="completed",
        final_status=values.get("final_status"),
        resolution_notes=values.get("resolution_notes"),
        **response_fields,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.post("/tickets", response_model=TicketResponse)
async def create_ticket(payload: TicketCreateRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": payload.ticket_id}}
    with trace_ticket_session(payload.customer_id, payload.ticket_id, issue_type="unknown"):
        traced_invoke(graph, {
            "ticket_id": payload.ticket_id, "channel": payload.channel,
            "customer_id": payload.customer_id, "raw_text": payload.raw_text,
        }, config)
    flush_traces()
    return _format_from_state(graph.get_state(config), payload.ticket_id)


@app.post("/tickets/{thread_id}/resume", response_model=TicketResponse)
async def resume_ticket(thread_id: str, payload: TicketResumeRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    if not state.next:
        raise HTTPException(status_code=409, detail="Ticket is not paused for approval")
    with trace_ticket_session(customer_id=thread_id, ticket_id=thread_id, issue_type="resume"):
        traced_invoke(graph, Command(resume={"approved": payload.approved, "note": payload.note}), config)
    flush_traces()
    return _format_from_state(graph.get_state(config), thread_id)


@app.get("/tickets/{thread_id}", response_model=TicketResponse)
async def get_ticket(thread_id: str):
    graph = app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    return _format_from_state(state, thread_id)
