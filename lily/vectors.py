"""Vector recall — semantic search over Lily's memory.

Embeddings come from the local embedding model (via Ollama) and are stored as
float32 BLOBs in the same SQLite database. Search embeds the query and ranks
stored vectors by cosine similarity. This is fully local and needs no native
extension; if ``sqlite-vec`` is ever installed it can replace the Python ranking
for speed, but the math here is the source of truth.
"""

import sqlite3
import struct
import time

from . import brain, memory
from .log import get_logger

log = get_logger("vectors")


class VectorUnavailable(Exception):
    """Raised when embeddings can't be produced (model missing / Ollama down)."""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(memory.DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL NOT NULL,
            source  TEXT NOT NULL,
            ref_id  INTEGER NOT NULL,
            text    TEXT NOT NULL,
            vec     BLOB NOT NULL,
            UNIQUE(source, ref_id, text)
        )
        """
    )
    return conn


def _to_blob(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _from_blob(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _rank(query_vec: list[float], rows: list[dict], k: int) -> list[dict]:
    """Pure: score each row by cosine to ``query_vec`` and return the top ``k``."""
    scored = [{**row, "score": _cosine(query_vec, row["vec"])} for row in rows]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:k]


def _embed(text: str) -> list[float]:
    try:
        vec = brain.embed(text)
    except brain.BrainOffline as exc:
        raise VectorUnavailable(str(exc)) from exc
    if not vec:
        raise VectorUnavailable("embedding model returned an empty vector")
    return vec


def index_text(text: str, source: str = "manual", ref_id: int = 0) -> bool:
    """Embed and store one piece of text. Returns False if it was already indexed."""
    text = text.strip()
    if not text:
        return False
    vec = _embed(text)
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO embeddings (ts, source, ref_id, text, vec) "
                "VALUES (?, ?, ?, ?, ?)",
                (time.time(), source, ref_id, text, _to_blob(vec)),
            )
            changed = conn.total_changes > 0
    finally:
        conn.close()
    return changed


def search(query: str, k: int = 5) -> list[dict]:
    """Return up to ``k`` stored texts most semantically similar to ``query``."""
    query_vec = _embed(query)
    conn = _conn()
    raw = conn.execute("SELECT source, ref_id, text, vec FROM embeddings").fetchall()
    conn.close()
    rows = [
        {"source": s, "ref_id": r, "text": t, "vec": _from_blob(v)} for s, r, t, v in raw
    ]
    return [
        {"source": row["source"], "ref_id": row["ref_id"], "text": row["text"], "score": row["score"]}
        for row in _rank(query_vec, rows, k)
    ]


def reindex_all() -> int:
    """Index everything in memory worth recalling (facts + project notes). Returns count."""
    indexed = 0
    for fact in memory.list_facts(limit=100):
        if index_text(f"[{fact['kind']}] {fact['content']}", source="fact", ref_id=fact["id"]):
            indexed += 1
    for project in memory.list_projects():
        for note in memory.project_notes(project, limit=100):
            label = f"[{project}] {note['content']}"
            if index_text(label, source="project_note", ref_id=note["id"]):
                indexed += 1
    log.info("reindexed %d new items", indexed)
    return indexed


def count() -> int:
    conn = _conn()
    n = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    conn.close()
    return int(n)
