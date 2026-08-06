"""
M1 — Triage Agent
Turns a raw ticket dict into a validated SupportTicket.
"""

from src.llm_client import extract_ticket_fields
from src.schemas import SupportTicket


def parse_ticket(ticket_id: str, channel: str, customer_id: str, raw_text: str) -> SupportTicket:
    extracted = extract_ticket_fields(raw_text)

    return SupportTicket(
        ticket_id=ticket_id,
        channel=channel,
        customer_id=customer_id,
        raw_text=raw_text,
        **extracted,
    )