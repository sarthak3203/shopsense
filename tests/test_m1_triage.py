import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.triage_agent import parse_ticket


def load_sample_tickets():
    path = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_all_sample_tickets_parse_and_validate():
    tickets = load_sample_tickets()
    assert len(tickets) > 0

    for t in tickets:
        parsed = parse_ticket(
            ticket_id=t["ticket_id"],
            channel=t["channel"],
            customer_id=t["customer_id"],
            raw_text=t["text"],
        )
        print(f"\n{t['ticket_id']}: {parsed.issue_type} | {parsed.sentiment} | "
              f"{parsed.urgency} | order={parsed.order_id} | "
              f"injection={parsed.suspected_prompt_injection}")
        assert parsed.ticket_id == t["ticket_id"]


def test_prompt_injection_ticket_is_flagged():
    tickets = load_sample_tickets()
    injection_ticket = next(t for t in tickets if t["ticket_id"] == "T-1006")
    parsed = parse_ticket(
        ticket_id=injection_ticket["ticket_id"],
        channel=injection_ticket["channel"],
        customer_id=injection_ticket["customer_id"],
        raw_text=injection_ticket["text"],
    )
    assert parsed.suspected_prompt_injection is True