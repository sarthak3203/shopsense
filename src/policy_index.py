"""
M3 — Policy retrieval foundation.
Answers "what does the company allow" — a Qdrant vector index over the
synthetic policy handbook. Kept deliberately separate from customer
memory (memory_store.py).

Uses Qdrant's embedded local mode (no server/Docker) with FastEmbed
for local, free, CPU-based embeddings.
"""

import json
from pathlib import Path

from qdrant_client import QdrantClient, models

_HANDBOOK_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_handbook.json"
_QDRANT_PATH = Path(__file__).resolve().parent.parent / ".qdrant_data"

COLLECTION_NAME = "policy_handbook"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_client = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=str(_QDRANT_PATH))
    return _client


def build_policy_index(force_rebuild: bool = False) -> None:
    """Loads the policy handbook and (re)builds the Qdrant collection."""
    client = get_client()

    exists = client.collection_exists(COLLECTION_NAME)
    if exists and not force_rebuild:
        return  # already built, nothing to do

    if exists and force_rebuild:
        client.delete_collection(COLLECTION_NAME)

    with open(_HANDBOOK_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=client.get_embedding_size(EMBEDDING_MODEL),
            distance=models.Distance.COSINE,
        ),
    )

    docs = [models.Document(text=c["text"], model=EMBEDDING_MODEL) for c in chunks]
    ids = list(range(len(chunks)))
    payload = [{"id": c["id"], "category": c["category"], "text": c["text"]} for c in chunks]

    client.upload_collection(
        collection_name=COLLECTION_NAME,
        vectors=docs,
        ids=ids,
        payload=payload,
    )


def query_policy(query_text: str, top_k: int = 3) -> list[dict]:
    """Returns the top_k most relevant policy chunks for a natural-language query."""
    client = get_client()
    build_policy_index()  # no-op if already built

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=models.Document(text=query_text, model=EMBEDDING_MODEL),
        limit=top_k,
    ).points

    return [
        {"score": r.score, "category": r.payload["category"], "text": r.payload["text"]}
        for r in results
    ]