REFUND_AUTO_APPROVE_THRESHOLD = 500.0
ANGRY_SENTIMENTS = {"angry"}
CRITICAL_URGENCY = {"critical"}
AMBIGUOUS_ISSUE_TYPES = {"complaint", "other"}


def review(ticket_state: dict) -> dict:
    reasons = []

    if ticket_state.get("suspected_prompt_injection"):
        reasons.append("suspected_prompt_injection")
    if ticket_state.get("sentiment") in ANGRY_SENTIMENTS:
        reasons.append("angry_sentiment")
    if ticket_state.get("urgency") in CRITICAL_URGENCY:
        reasons.append("critical_urgency")

    refund_amount = ticket_state.get("refund_amount") or 0
    if refund_amount and refund_amount > REFUND_AUTO_APPROVE_THRESHOLD:
        reasons.append(f"refund_amount_{refund_amount}_over_threshold")

    if ticket_state.get("escalation_reason"):
        reasons.append(ticket_state["escalation_reason"])
    if ticket_state.get("issue_type") in AMBIGUOUS_ISSUE_TYPES:
        reasons.append("ambiguous_issue_type")

    return {
        "requires_human": len(reasons) > 0,
        "escalation_reason": "; ".join(reasons) if reasons else None,
    }