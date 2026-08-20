"""Deterministic unit tests for M8 hard guardrails."""

import pytest

from src.escalation_reviewer_agent import REFUND_AUTO_APPROVE_THRESHOLD
from src.guardrails import (
    GuardrailViolation, check_policy_answer_guardrail, check_refund_guardrail,
    enforce_policy_answer_guardrail, enforce_refund_guardrail,
)


def test_refund_under_threshold_not_escalated_allowed():
    assert check_refund_guardrail(REFUND_AUTO_APPROVE_THRESHOLD - 1, False, None).allowed


def test_refund_over_threshold_without_approval_blocked():
    result = check_refund_guardrail(REFUND_AUTO_APPROVE_THRESHOLD + 1, True, None)
    assert not result.allowed
    assert "exceeds_threshold" in result.reason


def test_refund_over_threshold_not_escalated_blocked():
    assert not check_refund_guardrail(REFUND_AUTO_APPROVE_THRESHOLD + 1, False, {"approved": True}).allowed


def test_refund_over_threshold_with_approval_allowed():
    assert check_refund_guardrail(REFUND_AUTO_APPROVE_THRESHOLD + 1, True, {"approved": True}).allowed


def test_refund_over_threshold_with_rejection_blocked():
    assert not check_refund_guardrail(REFUND_AUTO_APPROVE_THRESHOLD + 1, True, {"approved": False}).allowed


def test_refund_small_amount_but_escalated_without_approval_blocked():
    result = check_refund_guardrail(20.0, True, None)
    assert not result.allowed
    assert result.reason == "ticket_was_escalated_but_not_human_approved"


def test_refund_small_amount_escalated_with_approval_allowed():
    assert check_refund_guardrail(20.0, True, {"approved": True}).allowed


def test_refund_amount_none_blocked():
    result = check_refund_guardrail(None, False, None)
    assert not result.allowed
    assert result.reason == "refund_amount_missing"


def test_refund_amount_negative_blocked():
    result = check_refund_guardrail(-5.0, False, None)
    assert not result.allowed
    assert result.reason == "refund_amount_negative"


def test_enforce_refund_guardrail_raises_on_violation():
    with pytest.raises(GuardrailViolation):
        enforce_refund_guardrail(999999.0, False, None)


def test_enforce_refund_guardrail_silent_on_pass():
    enforce_refund_guardrail(10.0, False, None)


def test_policy_answer_none_allowed():
    assert check_policy_answer_guardrail(None).allowed


def test_policy_answer_grounded_no_unsupported_claims_allowed():
    assert check_policy_answer_guardrail({"grounded": True, "unsupported_claims": []}).allowed


def test_policy_answer_not_grounded_blocked():
    result = check_policy_answer_guardrail({"grounded": False, "unsupported_claims": []})
    assert not result.allowed
    assert result.reason == "policy_answer_not_grounded"


def test_policy_answer_unsupported_claims_blocked_even_if_grounded_true():
    result = check_policy_answer_guardrail({"grounded": True, "unsupported_claims": ["a 50% loyalty bonus"]})
    assert not result.allowed
    assert "unsupported_claims" in result.reason


def test_enforce_policy_answer_guardrail_raises_on_violation():
    with pytest.raises(GuardrailViolation):
        enforce_policy_answer_guardrail({"grounded": False, "unsupported_claims": []})


def test_enforce_policy_answer_guardrail_silent_on_pass():
    enforce_policy_answer_guardrail({"grounded": True, "unsupported_claims": []})
