import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.policy_index import build_policy_index, hybrid_search_policy
from src.reranker import rerank


def test_hybrid_index_builds():
    build_policy_index(force_rebuild=True)


def test_hybrid_catches_exact_keyword_final_sale():
    """This is the case naive dense search (M3) is weakest on: an exact,
    distinctive keyword phrase. Sparse/BM25 should nail this."""
    results = hybrid_search_policy("Can I return a final sale item?", top_k=3)
    print("\nHYBRID RESULTS:")
    for r in results:
        print(f"  [{r['score']:.4f}] ({r['category']}) {r['text']}")
    assert any("final sale" in r["text"].lower() for r in results)


def test_rerank_reorders_by_true_relevance():
    candidates = hybrid_search_policy("What happens if my package is late?", top_k=5)
    top = rerank("What happens if my package is late?", candidates, top_k=3)
    print("\nRERANKED RESULTS:")
    for r in top:
        print(f"  [rerank={r['rerank_score']:.4f}] ({r['category']}) {r['text']}")
    assert len(top) <= 3
    assert any("10 business days" in r["text"] for r in top)