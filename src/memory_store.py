"""
M3 — Per-customer interaction memory.
Answers "what do we know about this customer" — completely separate
from policy knowledge (which lives in policy_index.py / Qdrant).

Simple JSON-file-backed store. Good enough for a demo/portfolio system;
swappable for a real database later without changing the interface.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_MEMORY_PATH = Path(__file__).resolve().parent.parent / "data" / "customer_memory.json"


def _load_all() -> dict:
    with open(_MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict) -> None:
    with open(_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def get_customer_context(customer_id: str) -> dict:
    """Returns this customer's history. Empty defaults if never seen before."""
    all_memory = _load_all()
    return all_memory.get(customer_id, {"past_tickets": [], "preferences": {}})


def record_ticket(customer_id: str, ticket_id: str, issue_type: str, summary: str) -> None:
    """Append a resolved/seen ticket to this customer's history."""
    all_memory = _load_all()
    customer = all_memory.setdefault(customer_id, {"past_tickets": [], "preferences": {}})

    customer["past_tickets"].append({
        "ticket_id": ticket_id,
        "issue_type": issue_type,
        "summary": summary,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    all_memory[customer_id] = customer
    _save_all(all_memory)


def set_preference(customer_id: str, key: str, value: str) -> None:
    """Store a stated customer preference, e.g. preferred_contact='email'."""
    all_memory = _load_all()
    customer = all_memory.setdefault(customer_id, {"past_tickets": [], "preferences": {}})
    customer["preferences"][key] = value
    all_memory[customer_id] = customer
    _save_all(all_memory)