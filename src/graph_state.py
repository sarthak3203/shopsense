"""
Module 5 — LangGraph shared state schema.

TicketState flows through every node in the graph. Each node reads the fields
it needs and returns a partial dict; LangGraph merges it into the running state.
"""

from typing import TypedDict, Optional


class TicketState(TypedDict, total=False):
    # ---- input ----
    ticket_id: str
    channel: str          # "chat" | "email"
    customer_id: str
    raw_text: str

    # ---- after triage_node (M1) ----
    ticket: dict            # SupportTicket.model_dump()
    issue_type: str
    order_id: Optional[str]
    sentiment: str
    urgency: str
    suspected_prompt_injection: bool
    extraction_confidence: float

    # ---- customer memory (M3) ----
    customer_context: dict

    # ---- after policy_check_node (M4) ----
    policy_answer: Optional[dict]

    # ---- after action_node (M2) ----
    order_info: Optional[dict]
    shipping_info: Optional[dict]
    refund_amount: Optional[float]
    proposed_action: Optional[str]   # "refund" | "info_only" | "none"

    # ---- escalation ----
    requires_human: bool
    escalation_reason: Optional[str]

    # ---- human approval (interrupt) ----
    human_decision: Optional[dict]   # {"approved": bool, "note": str}

    # ---- final ----
    final_status: str                # "auto_resolved" | "human_approved" | "human_rejected"
    resolution_notes: Optional[str]