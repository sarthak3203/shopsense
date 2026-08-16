"""
M4 — Cross-encoder reranking.
Hybrid search gives good candidates fast, but fusion scores from two
independent retrievers are still an approximation. A cross-encoder reads
the query and each candidate document together (not independently), which
is slower but meaningfully more precise — so we use it as a final polish
step on a small candidate set, not for the initial retrieval.
"""

from fastembed.rerank.cross_encoder import TextCrossEncoder

_RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
_encoder = None


def get_encoder() -> TextCrossEncoder:
    global _encoder
    if _encoder is None:
        _encoder = TextCrossEncoder(model_name=_RERANK_MODEL)
    return _encoder


def rerank(query: str, candidates: list[dict], top_k: int = 3) -> list[dict]:
    """candidates: list of dicts with a 'text' key (from hybrid_search_policy)."""
    if not candidates:
        return []

    encoder = get_encoder()
    texts = [c["text"] for c in candidates]
    scores = list(encoder.rerank(query, texts))

    reranked = [{**c, "rerank_score": float(score)} for c, score in zip(candidates, scores)]
    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:top_k]