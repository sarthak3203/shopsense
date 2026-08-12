import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.policy_index import build_policy_index, query_policy


def test_index_builds_without_error():
    build_policy_index(force_rebuild=True)


def test_electronics_return_window_query():
    results = query_policy("What is the return window for electronics?", top_k=2)
    print("\nRESULTS:")
    for r in results:
        print(f"  [{r['score']:.3f}] ({r['category']}) {r['text']}")

    assert any("15 days" in r["text"] for r in results)


def test_warranty_accidental_damage_query():
    results = query_policy("Is accidental damage covered under warranty?", top_k=2)
    print("\nRESULTS:")
    for r in results:
        print(f"  [{r['score']:.3f}] ({r['category']}) {r['text']}")

    assert any("accidental damage" in r["text"].lower() for r in results)


def test_shipping_delay_query():
    results = query_policy("My package hasn't arrived, what happens?", top_k=2)
    print("\nRESULTS:")
    for r in results:
        print(f"  [{r['score']:.3f}] ({r['category']}) {r['text']}")

    assert any("10 business days" in r["text"] for r in results)