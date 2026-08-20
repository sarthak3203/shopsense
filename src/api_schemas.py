"""Pydantic wire models for the M8 FastAPI service."""

from typing import Literal, Optional
from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    ticket_id: str
    channel: Literal["chat", "email"]
    customer_id: str
    raw_text: str


class TicketResumeRequest(BaseModel):
    approved: bool
    note: str = ""


class TicketResponse(BaseModel):
    thread_id: str
    status: Literal["completed", "paused_for_approval"]
    requires_human: bool = False
    interrupt_payload: Optional[dict] = None
    final_status: Optional[str] = None
    resolution_notes: Optional[str] = None
    escalation_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    proposed_action: Optional[str] = None
    issue_type: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    suspected_prompt_injection: Optional[bool] = None
    policy_answer: Optional[dict] = None
    order_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
