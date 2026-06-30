"""Instant local retrieval tools."""

from .. import retrieval
from . import tool


@tool(description="Find local files or PDFs by filename and lightweight content search.")
def find_local_file(query: str, limit: int = 10) -> str:
    return retrieval.format_hits(retrieval.find(query, limit))
