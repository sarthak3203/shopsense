from src.escalation_reviewer_agent import review, REFUND_AUTO_APPROVE_THRESHOLD


def test_low_risk_ticket_does_not_escalate():
    result = review({
        "sentiment": "neutral",
        "urgency": "low",
        "issue_type": "shipping_status",
        "refund_amount": 0,
        "suspected_prompt_injection": False,
    })
    assert result["requires_human"] is False


def test_high_refund_escalates():
    result = review({
        "sentiment": "neutral",
        "urgency": "low",
        "issue_type": "refund_request",
        "refund_amount": REFUND_AUTO_APPROVE_THRESHOLD + 1,
        "suspected_prompt_injection": False,
    })
    assert result["requires_human"] is True
    assert "over_threshold" in result["escalation_reason"]


def test_angry_sentiment_escalates_regardless_of_amount():
    result = review({
        "sentiment": "angry",
        "urgency": "low",
        "issue_type": "refund_request",
        "refund_amount": 10,
        "suspected_prompt_injection": False,
    })
    assert result["requires_human"] is True
    assert "angry_sentiment" in result["escalation_reason"]


def test_prompt_injection_always_escalates():
    result = review({
        "sentiment": "neutral",
        "urgency": "low",
        "issue_type": "other",
        "refund_amount": 0,
        "suspected_prompt_injection": True,
    })
    assert result["requires_human"] is True
    assert "suspected_prompt_injection" in result["escalation_reason"]