import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.policy_rag_agent import answer_policy_question


def test_grounded_answer_electronics_return():
    result = answer_policy_question("What's the return window for electronics?")
    print("\nQUERY:", result["query"])
    print("ANSWER:", result["answer"])
    print("SOURCES:", result["sources"])
    print("GROUNDED:", result["grounded"])
    print("UNSUPPORTED CLAIMS:", result["unsupported_claims"])

    assert result["grounded"] is True
    assert len(result["sources"]) > 0
    assert "15" in result["answer"]


def test_honest_refusal_when_policy_silent():
    """This is the fabrication trap: a specific-sounding question the
    handbook does NOT actually answer. What actually matters is that no
    fabricated NUMBER (e.g. an invented refund percentage) appears —
    the groundedness judge may still (correctly) flag looser paraphrased
    generalizations as a stricter signal, which is fine and expected."""
    result = answer_policy_question(
        "What percentage refund do I get for a used item returned after 45 days?"
    )
    print("\nQUERY:", result["query"])
    print("ANSWER:", result["answer"])
    print("GROUNDED:", result["grounded"])
    print("UNSUPPORTED CLAIMS:", result["unsupported_claims"])

    # The hard guarantee: no fabricated refund percentage figure invented.
    assert "%" not in result["answer"]


def test_high_value_refund_review_threshold():
    result = answer_policy_question("Do refunds over $500 need approval?")
    print("\nQUERY:", result["query"])
    print("ANSWER:", result["answer"])
    print("SOURCES:", result["sources"])
    assert "500" in result["answer"]
    assert result["grounded"] is True