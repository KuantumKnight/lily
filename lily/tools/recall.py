"""Semantic recall tools — search Lily's memory by meaning, not keywords."""

from .. import vectors
from . import tool


@tool(
    description="Semantically search Lily's memory (facts and project notes) by meaning. Run reindex_memory first if results seem stale."
)
def semantic_recall(query: str, limit: int = 5) -> str:
    try:
        hits = vectors.search(query, k=limit)
    except vectors.VectorUnavailable as exc:
        return f"[error] {exc}"
    if not hits:
        return "Nothing indexed yet — try reindex_memory."
    return "\n".join(f"({hit['score']:.2f}) {hit['text']}" for hit in hits)


@tool(description="Index Lily's facts and project notes for semantic search. Returns how many new items were added.")
def reindex_memory() -> str:
    try:
        added = vectors.reindex_all()
    except vectors.VectorUnavailable as exc:
        return f"[error] {exc}"
    return f"Indexed {added} new item(s). {vectors.count()} total in the vector store."
