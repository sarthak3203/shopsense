"""
M4 — Production-Grade RAG: hybrid search (dense + sparse) with RRF fusion.
Upgrades M3's naive vector search into dense+sparse hybrid retrieval —
sparse (BM25-style) catches exact keyword matches naive dense search misses
(e.g. "final sale"), dense catches semantic matches sparse misses.
"""

import json
from pathlib import Path

from qdrant_client import QdrantClient, models

_HANDBOOK_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_handbook.json"
_QDRANT_PATH = Path(__file__).resolve().parent.parent / ".qdrant_data"

COLLECTION_NAME = "policy_handbook_hybrid"
DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"

_client = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=str(_QDRANT_PATH))
    return _client


def build_policy_index(force_rebuild: bool = False) -> None:
    client = get_client()

    exists = client.collection_exists(COLLECTION_NAME)
    if exists and not force_rebuild:
        return

    if exists and force_rebuild:
        client.delete_collection(COLLECTION_NAME)

    with open(_HANDBOOK_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=client.get_embedding_size(DENSE_MODEL),
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF),
        },
    )

    points = [
        models.PointStruct(
            id=i,
            vector={
                "dense": models.Document(text=c["text"], model=DENSE_MODEL),
                "sparse": models.Document(text=c["text"], model=SPARSE_MODEL),
            },
            payload={"id": c["id"], "category": c["category"], "text": c["text"]},
        )
        for i, c in enumerate(chunks)
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)


def hybrid_search_policy(query_text: str, top_k: int = 5) -> list[dict]:
    """Dense + sparse hybrid retrieval, fused with Reciprocal Rank Fusion."""
    client = get_client()
    build_policy_index()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=models.Document(text=query_text, model=DENSE_MODEL),
                using="dense",
                limit=top_k * 2,
            ),
            models.Prefetch(
                query=models.Document(text=query_text, model=SPARSE_MODEL),
                using="sparse",
                limit=top_k * 2,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k,
    ).points

    return [
        {"score": r.score, "id": r.payload["id"], "category": r.payload["category"], "text": r.payload["text"]}
        for r in results
    ]