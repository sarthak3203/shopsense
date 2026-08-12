import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.memory_store import get_customer_context, record_ticket, set_preference


def test_new_customer_has_empty_context():
    context = get_customer_context("C-999-nonexistent")
    assert context["past_tickets"] == []
    assert context["preferences"] == {}


def test_record_and_retrieve_ticket_history():
    record_ticket("C-TEST-01", "T-9001", "refund_request", "Broken blender, wants refund")
    record_ticket("C-TEST-01", "T-9002", "shipping_status", "Asking where package is")

    context = get_customer_context("C-TEST-01")
    print("\nPAST TICKETS:", context["past_tickets"])

    assert len(context["past_tickets"]) >= 2
    issue_types = [t["issue_type"] for t in context["past_tickets"]]
    assert "refund_request" in issue_types
    assert "shipping_status" in issue_types


def test_preferences_persist():
    set_preference("C-TEST-01", "preferred_contact", "email")
    context = get_customer_context("C-TEST-01")
    print("\nPREFERENCES:", context["preferences"])
    assert context["preferences"]["preferred_contact"] == "email"