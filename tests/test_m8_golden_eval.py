import pytest

from src.eval_runner import evaluate_ticket, load_golden_tickets, run_ticket

GOLDEN_TICKETS = load_golden_tickets()


@pytest.mark.parametrize("ticket", GOLDEN_TICKETS, ids=[t["ticket_id"] for t in GOLDEN_TICKETS])
def test_golden_ticket(ticket):
    result = run_ticket(ticket)
    failures = evaluate_ticket(ticket, result)
    assert not failures, f"{ticket['ticket_id']} ({ticket['category']}) failed:\n  " + "\n  ".join(failures)


def test_golden_set_has_twenty_tickets():
    assert len(GOLDEN_TICKETS) == 20


def test_golden_set_ticket_ids_unique():
    ids = [t["ticket_id"] for t in GOLDEN_TICKETS]
    assert len(ids) == len(set(ids))
