"""
M4 — Policy RAG Agent (production-grade).
Pipeline: hybrid search -> rerank -> grounded answer generation -> groundedness check.
The groundedness check is a second, independent LLM call acting as a strict
fact-checker — this is the mechanism that catches fabrication before it
ever reaches a customer.
"""

import json
import os

from dotenv import load_dotenv
from litellm import completion
from litellm.exceptions import RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.policy_index import hybrid_search_policy
from src.reranker import rerank

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-120b")


def _generate_answer(query: str, chunks: list[dict]) -> str:
    context = "\n".join(f"[{c['id']}] {c['text']}" for c in chunks)
    system_prompt = (
        "You are a policy Q&A assistant for an e-commerce support system. "
        "Answer ONLY using the provided policy excerpts below. "
        "Never invent a number, window, or term that isn't in the excerpts. "
        "If you must combine two cited numbers (e.g. a base window plus an "
        "extension) into a total, show the arithmetic explicitly next to both "
        "citations, e.g. '15 days [policy-002] + 15 days [policy-010] = 30 days', "
        "rather than stating the combined total as a bare fact. "
        "If the excerpts don't answer the question, say so explicitly instead of guessing. "
        "Cite the excerpt id(s) you used in square brackets, e.g. [policy-002]."
    )
    user_prompt = f"Policy excerpts:\n{context}\n\nQuestion: {query}"

    response = _completion_with_rate_limit_retry(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


def _groundedness_check(query: str, answer: str, chunks: list[dict]) -> dict:
    """LLM-as-judge: is every factual claim in the answer actually supported
    by the retrieved chunks?"""
    context = "\n".join(f"[{c['id']}] {c['text']}" for c in chunks)
    judge_prompt = (
        "You are a strict fact-checker. Given the SOURCE EXCERPTS and an ANSWER, "
        "determine if every factual claim in the ANSWER (numbers, windows, terms, "
        "eligibility rules) is directly supported by the SOURCE EXCERPTS. "
        "Simple arithmetic that combines two numbers which are BOTH explicitly "
        "cited from the source excerpts (e.g. a stated base window plus a stated "
        "extension) counts as grounded, not fabricated — as long as both source "
        "numbers appear with their citations in the answer. "
        "A claim only counts as unsupported if it introduces information, a number, "
        "or a rule that cannot be traced back to the excerpts at all. "
        "Respond with ONLY JSON, no prose, no markdown fences: "
        '{"grounded": boolean, "unsupported_claims": [list of strings, empty if none]}'
    )
    user_prompt = f"SOURCE EXCERPTS:\n{context}\n\nQUESTION: {query}\n\nANSWER:\n{answer}"

    response = _completion_with_rate_limit_retry(
        model=MODEL,
        messages=[
            {"role": "system", "content": judge_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content.strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(content)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    reraise=True,
)
def _completion_with_rate_limit_retry(**kwargs):
    return completion(**kwargs)


def answer_policy_question(query: str, top_k: int = 3) -> dict:
    """Full production-grade RAG pipeline for a single policy question."""
    candidates = hybrid_search_policy(query, top_k=top_k * 2)
    top_chunks = rerank(query, candidates, top_k=top_k)

    answer = _generate_answer(query, top_chunks)
    groundedness = _groundedness_check(query, answer, top_chunks)

    return {
        "query": query,
        "answer": answer,
        "sources": [c["id"] for c in top_chunks],
        "retrieved_chunks": top_chunks,
        "grounded": groundedness["grounded"],
        "unsupported_claims": groundedness.get("unsupported_claims", []),
    }
