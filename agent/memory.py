"""Retrieval and storage logic backed by ChromaDB + sentence-transformers.

Memory holds past generated outputs that scored well, embedded by their brand
brief. On each new run we retrieve the top-k most similar high-scoring entries
and feed them back as few-shot examples — this is the substrate of the
self-improving loop.

Only entries scoring above RETRIEVAL_SCORE_FLOOR (3.5/5) are ever stored or
returned, so the agent only learns from outputs that actually worked.
"""

import os

# sentence-transformers pulls in `transformers`, which will try to import a
# TensorFlow/Keras backend if one is present. We only use the PyTorch path, so
# disable the TF backend before anything imports transformers. (Avoids the
# "Keras 3 is not supported" import error in envs that have TF/Keras 3.)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import json
import uuid
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = "ad_copy_memory"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Minimum weighted score for an entry to live in / be retrieved from memory.
RETRIEVAL_SCORE_FLOOR = 3.5


def _brief_to_text(brief: dict[str, Any]) -> str:
    """Flatten a brand brief into a single string used for embedding."""
    parts = [
        brief.get("brand", ""),
        brief.get("product", ""),
        brief.get("audience", ""),
        brief.get("tone", ""),
        brief.get("goal", ""),
    ]
    return " | ".join(str(p) for p in parts if p)


class Memory:
    """Vector memory of high-scoring ad copy, keyed by brief similarity."""

    def __init__(self, persist_dir: str = CHROMA_DIR):
        self._client = chromadb.PersistentClient(path=persist_dir)
        # sentence-transformers embedding function, computed locally.
        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        brief: dict[str, Any],
        variant_type: str,
        output: str,
        score: float,
        prompt_version: str,
        timestamp: str,
    ) -> bool:
        """Store one high-scoring output. Returns False if below the floor."""
        if score < RETRIEVAL_SCORE_FLOOR:
            return False

        self._collection.add(
            ids=[str(uuid.uuid4())],
            documents=[output],
            metadatas=[
                {
                    "brief": json.dumps(brief),
                    "variant_type": variant_type,
                    "score": float(score),
                    "prompt_version": prompt_version,
                    "timestamp": timestamp,
                }
            ],
        )
        return True

    def retrieve(self, brief: dict[str, Any], k: int = 3) -> list[dict[str, Any]]:
        """Return up to k most similar past entries with score >= the floor.

        Results are ordered by vector similarity to the incoming brief.
        """
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(
            query_texts=[_brief_to_text(brief)],
            # Over-fetch so the score filter still leaves us close to k.
            n_results=min(max(k * 3, k), count),
            where={"score": {"$gte": RETRIEVAL_SCORE_FLOOR}},
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        examples: list[dict[str, Any]] = []
        for doc, meta in zip(docs, metas):
            examples.append(
                {
                    "brief": json.loads(meta.get("brief", "{}")),
                    "variant_type": meta.get("variant_type", "output"),
                    "output": doc,
                    "score": meta.get("score", 0.0),
                    "prompt_version": meta.get("prompt_version", ""),
                }
            )
            if len(examples) >= k:
                break
        return examples

    def count(self) -> int:
        return self._collection.count()
