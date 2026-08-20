"""
Module 5 — LangGraph workflow. Updated in M7 with:
  - @observe() tracing on every node (Langfuse)
  - action_node / resolve_node now call the resilient order_system_client
    wrappers (retries + circuit breaker) instead of mock_apis directly,
    and catch BackendUnavailableError to fall back to human escalation
    instead of crashing the pipeline.

triage -> [policy_check] -> action -> escalation_check -> [human_approval] -> resolve/reject

Low-risk tickets (small/no refund, non-angry, non-critical, no injection flag,
no eligibility problem, no backend outage) auto-resolve. High-refund,
angry-sentiment, ineligible-refund, or order-system-unavailable tickets pause
at human_approval via interrupt() and require Command(resume=...) to continue.
State is checkpointed via the caller-supplied checkpointer (SqliteSaver in
production use, so a paused ticket survives a process restart).
"""

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from src.graph_state import TicketState
from src.triage_agent import parse_ticket
from src.order_system_client import (
    order_lookup,
    get_shipping_status,
    calculate_refund_amount,
    initiate_refund_or_replacement,
    BackendUnavailableError,
)
from src.memory_store import get_customer_context, record_ticket
from src.policy_rag_agent import answer_policy_question
from src.escalation_reviewer_agent import review as escalation_review
from src.tracing import observe
from src.guardrails import (
    GuardrailViolation,
    check_policy_answer_guardrail,
    enforce_refund_guardrail,
)


# ---------------------------------------------------------------- triage ---
@observe(name="triage_node")
def triage_node(state: TicketState) -> dict:
    ticket = parse_ticket(
        ticket_id=state["ticket_id"],
        channel=state["channel"],
        customer_id=state["customer_id"],
        raw_text=state["raw_text"],
    )
    ticket_dict = ticket.model_dump()
    context = get_customer_context(state["customer_id"])

    return {
        "ticket": ticket_dict,
        "issue_type": ticket_dict["issue_type"],
        "order_id": ticket_dict.get("order_id"),
        "sentiment": ticket_dict["sentiment"],
        "urgency": ticket_dict["urgency"],
        "suspected_prompt_injection": ticket_dict.get("suspected_prompt_injection", False),
        "extraction_confidence": ticket_dict.get("extraction_confidence", 0.0),
        "customer_context": context,
    }


def route_after_triage(state: TicketState) -> str:
    if state.get("suspected_prompt_injection"):
        return "escalation_check"
    issue_type = state.get("issue_type")
    if issue_type in ("general_policy_question", "warranty_claim"):
        return "policy_check"
    if issue_type in ("refund_request", "return_request", "shipping_status", "order_status"):
        return "action"
    return "escalation_check"  # complaint / other / anything unrecognized


# ---------------------------------------------------------- policy check ---
@observe(name="policy_check_node")
def policy_check_node(state: TicketState) -> dict:
    query = state["ticket"].get("summary") or state["raw_text"]
    result = answer_policy_question(query)
    guardrail = check_policy_answer_guardrail(result)
    if not guardrail.allowed:
        # Do not retain an unsafe policy answer in state where a future node
        # could surface or rely on it. The escalation reviewer will require a
        # human because escalation_reason is non-empty.
        return {
            "policy_answer": None,
            "escalation_reason": f"policy_guardrail: {guardrail.reason}",
        }
    return {"policy_answer": result}


def route_after_policy(state: TicketState) -> str:
    policy_answer = state.get("policy_answer") or {}
    grounded_and_clean = policy_answer.get("grounded", False) and not policy_answer.get(
        "unsupported_claims"
    )

    if state.get("issue_type") == "warranty_claim" and grounded_and_clean:
        return "action"
    return "escalation_check"


# ---------------------------------------------------------------- action ---
@observe(name="action_node")
def action_node(state: TicketState) -> dict:
    order_id = state.get("order_id")
    issue_type = state.get("issue_type")

    if not order_id:
        return {"proposed_action": "none", "escalation_reason": "no_order_id_found"}

    try:
        if issue_type == "shipping_status":
            return {"shipping_info": get_shipping_status(order_id), "proposed_action": "info_only"}

        if issue_type == "order_status":
            return {"order_info": order_lookup(order_id), "proposed_action": "info_only"}

        if issue_type in ("refund_request", "return_request", "warranty_claim"):
            order_info = order_lookup(order_id)
            refund_calc = calculate_refund_amount(order_id)

            if not refund_calc.get("found"):
                return {
                    "order_info": order_info,
                    "proposed_action": "none",
                    "escalation_reason": refund_calc.get("error", "order_not_found"),
                }

            eligible = refund_calc.get("eligible", False)
            amount = refund_calc.get("refund_amount", 0.0)
            reason = refund_calc.get("reason", "")

            return {
                "order_info": order_info,
                "refund_amount": amount,
                "proposed_action": "refund" if eligible else "none",
                "escalation_reason": None if eligible else f"refund_ineligible: {reason}",
            }

        return {"proposed_action": "none"}

    except BackendUnavailableError as e:
        # Retries + circuit breaker (src/reliability.py) already exhausted
        # inside order_system_client. Never crash the pipeline on a backend
        # outage -- fall back to human review instead. escalation_review()
        # already checks state["escalation_reason"] and will set
        # requires_human=True because this reason is non-empty.
        return {
            "proposed_action": "none",
            "escalation_reason": f"order_system_unavailable: {e}",
        }


# ----------------------------------------------------------- escalation ---
@observe(name="escalation_check_node")
def escalation_check_node(state: TicketState) -> dict:
    return escalation_review(state)


def route_after_escalation_check(state: TicketState) -> str:
    return "human_approval" if state.get("requires_human") else "resolve"


# ------------------------------------------------------- human approval ---
@observe(name="human_approval_node")
def human_approval_node(state: TicketState) -> dict:
    decision = interrupt(
        {
            "ticket_id": state["ticket_id"],
            "customer_id": state["customer_id"],
            "issue_type": state.get("issue_type"),
            "sentiment": state.get("sentiment"),
            "proposed_action": state.get("proposed_action"),
            "refund_amount": state.get("refund_amount"),
            "escalation_reason": state.get("escalation_reason"),
            "message": "Human approval required. Resume with "
                       "Command(resume={'approved': bool, 'note': str}).",
        }
    )
    return {"human_decision": decision}


def route_after_human_approval(state: TicketState) -> str:
    decision = state.get("human_decision") or {}
    return "resolve" if decision.get("approved") else "reject"


# -------------------------------------------------------------- resolve ---
@observe(name="resolve_node")
def resolve_node(state: TicketState) -> dict:
    order_id = state.get("order_id")
    proposed_action = state.get("proposed_action")
    was_escalated = bool(state.get("requires_human"))
    notes = "Human-approved" if was_escalated else "Auto-resolved"

    if proposed_action == "refund" and order_id:
        try:
            enforce_refund_guardrail(
                amount=state.get("refund_amount"),
                was_escalated=was_escalated,
                human_decision=state.get("human_decision"),
            )
            result = initiate_refund_or_replacement(
                order_id=order_id,
                action="refund",
                amount=state.get("refund_amount"),
            )
            notes += f" — refund executed: {result}"
        except GuardrailViolation as e:
            notes += (
                f" — refund BLOCKED by guardrail: {e}. Needs manual review. "
                f"This should not be reachable if routing/escalation logic "
                f"is correct — treat as a bug if it ever fires in production."
            )
        except BackendUnavailableError as e:
            # Human already approved, but the backend is down at execution
            # time. Don't silently claim success -- record the failure
            # clearly so it's picked up for manual follow-up.
            notes += (
                f" — refund execution FAILED (order system unavailable: {e}). "
                f"Needs manual follow-up."
            )

    record_ticket(
        state["customer_id"],
        ticket_id=state["ticket_id"],
        issue_type=state.get("issue_type"),
        summary=notes,
    )

    return {
        "final_status": "human_approved" if was_escalated else "auto_resolved",
        "resolution_notes": notes,
    }


@observe(name="reject_node")
def reject_node(state: TicketState) -> dict:
    decision = state.get("human_decision") or {}
    notes = f"Human rejected the proposed action. Note: {decision.get('note', '')}"

    record_ticket(
        state["customer_id"],
        ticket_id=state["ticket_id"],
        issue_type=state.get("issue_type"),
        summary=notes,
    )

    return {"final_status": "human_rejected", "resolution_notes": notes}


# ---------------------------------------------------------------- graph ---
def build_graph(checkpointer):
    graph = StateGraph(TicketState)

    graph.add_node("triage", triage_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("action", action_node)
    graph.add_node("escalation_check", escalation_check_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("resolve", resolve_node)
    graph.add_node("reject", reject_node)

    graph.set_entry_point("triage")

    graph.add_conditional_edges(
        "triage", route_after_triage,
        {"policy_check": "policy_check", "action": "action", "escalation_check": "escalation_check"},
    )
    graph.add_conditional_edges(
        "policy_check", route_after_policy,
        {"action": "action", "escalation_check": "escalation_check"},
    )
    graph.add_edge("action", "escalation_check")
    graph.add_conditional_edges(
        "escalation_check", route_after_escalation_check,
        {"human_approval": "human_approval", "resolve": "resolve"},
    )
    graph.add_conditional_edges(
        "human_approval", route_after_human_approval,
        {"resolve": "resolve", "reject": "reject"},
    )
    graph.add_edge("resolve", END)
    graph.add_edge("reject", END)

    return graph.compile(checkpointer=checkpointer)
