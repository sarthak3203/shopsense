"""Hard-enforcement guardrails for ShopSense's two non-negotiables."""

from dataclasses import dataclass
from typing import Optional

from src.escalation_reviewer_agent import REFUND_AUTO_APPROVE_THRESHOLD


class GuardrailViolation(Exception):
    """Raised when an action would violate a hard non-negotiable."""


@dataclass
class GuardrailResult:
    allowed: bool
    reason: Optional[str] = None


def check_refund_guardrail(amount: Optional[float], was_escalated: bool, human_decision: Optional[dict]) -> GuardrailResult:
    """Check whether a refund is allowed immediately before execution."""
    if amount is None:
        return GuardrailResult(False, "refund_amount_missing")
    if amount < 0:
        return GuardrailResult(False, "refund_amount_negative")
    approved = bool((human_decision or {}).get("approved"))
    if amount > REFUND_AUTO_APPROVE_THRESHOLD:
        if not (was_escalated and approved):
            return GuardrailResult(False, f"refund_amount_{amount}_exceeds_threshold_{REFUND_AUTO_APPROVE_THRESHOLD}_without_human_approval")
        return GuardrailResult(True)
    if was_escalated and not approved:
        return GuardrailResult(False, "ticket_was_escalated_but_not_human_approved")
    return GuardrailResult(True)


def check_policy_answer_guardrail(policy_answer: Optional[dict]) -> GuardrailResult:
    """Check whether a policy answer may be trusted or surfaced."""
    if not policy_answer:
        return GuardrailResult(True)
    if not policy_answer.get("grounded", False):
        return GuardrailResult(False, "policy_answer_not_grounded")
    unsupported = policy_answer.get("unsupported_claims") or []
    if unsupported:
        return GuardrailResult(False, f"policy_answer_has_unsupported_claims: {unsupported}")
    return GuardrailResult(True)


def enforce_refund_guardrail(amount: Optional[float], was_escalated: bool, human_decision: Optional[dict]) -> None:
    """Raise GuardrailViolation when refund execution is unsafe."""
    result = check_refund_guardrail(amount, was_escalated, human_decision)
    if not result.allowed:
        raise GuardrailViolation(result.reason)


def enforce_policy_answer_guardrail(policy_answer: Optional[dict]) -> None:
    """Raise GuardrailViolation when a policy answer is unsafe."""
    result = check_policy_answer_guardrail(policy_answer)
    if not result.allowed:
        raise GuardrailViolation(result.reason)
