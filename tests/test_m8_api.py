import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace

from src.main import _format_from_state, app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_ticket_auto_resolve(client):
    resp = client.post("/tickets", json={"ticket_id": "API-TEST-001", "channel": "chat", "customer_id": "CUST-API-01", "raw_text": "I'd like a refund for order ORD-9002, it's within the return window."})
    assert resp.status_code == 200
    assert resp.json()["thread_id"] == "API-TEST-001"
    assert resp.json()["status"] in ("completed", "paused_for_approval")


def test_create_ticket_triggers_pause(client):
    resp = client.post("/tickets", json={"ticket_id": "API-TEST-002", "channel": "email", "customer_id": "CUST-API-02", "raw_text": "Please refund order ORD-8842, it's damaged."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "paused_for_approval"
    assert body["requires_human"] is True
    assert body["interrupt_payload"] is not None


def test_resume_paused_ticket(client):
    create_resp = client.post("/tickets", json={"ticket_id": "API-TEST-003", "channel": "email", "customer_id": "CUST-API-03", "raw_text": "Please refund order ORD-8842, it's damaged."})
    assert create_resp.json()["status"] == "paused_for_approval"
    resume_resp = client.post("/tickets/API-TEST-003/resume", json={"approved": True, "note": "Verified damage via photo, approving."})
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "completed"
    assert resume_resp.json()["final_status"] == "human_approved"


def test_resume_unknown_thread_returns_error(client):
    resp = client.post("/tickets/DOES-NOT-EXIST/resume", json={"approved": True, "note": "n/a"})
    assert resp.status_code in (404, 409)


def test_get_unknown_ticket_returns_404(client):
    assert client.get("/tickets/NEVER-CREATED").status_code == 404


def test_get_completed_ticket(client):
    client.post("/tickets", json={"ticket_id": "API-TEST-004", "channel": "chat", "customer_id": "CUST-API-04", "raw_text": "What is your standard return window?"})
    resp = client.get("/tickets/API-TEST-004")
    assert resp.status_code == 200
    assert resp.json()["thread_id"] == "API-TEST-004"


def test_format_from_state_preserves_policy_and_triage_fields():
    policy_answer = {
        "query": "What is the return window?",
        "answer": "Standard orders may be returned within 30 days.",
        "sources": ["policy-002"],
        "retrieved_chunks": [],
        "grounded": True,
        "unsupported_claims": [],
    }
    snapshot = SimpleNamespace(
        values={
            "requires_human": False,
            "final_status": "auto_resolved",
            "resolution_notes": "Answered the policy question.",
            "urgency": "low",
            "suspected_prompt_injection": False,
            "policy_answer": policy_answer,
        },
        next=(),
        tasks=(),
    )

    response = _format_from_state(snapshot, "API-STATE-001")

    assert response.status == "completed"
    assert response.urgency == "low"
    assert response.suspected_prompt_injection is False
    assert response.policy_answer == policy_answer


def test_format_from_state_enriches_paused_interrupt_payload():
    policy_answer = {"answer": "A grounded answer.", "sources": ["policy-002"], "grounded": True}
    snapshot = SimpleNamespace(
        values={
            "requires_human": True,
            "urgency": "critical",
            "suspected_prompt_injection": True,
            "policy_answer": policy_answer,
        },
        next=("human_approval",),
        tasks=(SimpleNamespace(interrupts=(SimpleNamespace(value={"reason": "manual review"}),)),),
    )

    response = _format_from_state(snapshot, "API-STATE-002")

    assert response.status == "paused_for_approval"
    assert response.interrupt_payload == {
        "reason": "manual review",
        "issue_type": None,
        "sentiment": None,
        "urgency": "critical",
        "suspected_prompt_injection": True,
        "proposed_action": None,
        "refund_amount": None,
        "escalation_reason": None,
        "policy_answer": policy_answer,
    }
