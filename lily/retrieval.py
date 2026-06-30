"""Instant local retrieval for files and documents."""

from pathlib import Path

from .config import DATA_DIR, ROOT

SEARCH_ROOTS = (ROOT, DATA_DIR)
TEXT_SUFFIXES = {".txt", ".md", ".toml", ".py", ".json", ".csv", ".log"}
PDF_SUFFIX = ".pdf"


def find(query: str, limit: int = 10) -> list[dict]:
    """Find local files by name and lightweight text/PDF content."""
    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        return []
    hits: list[dict] = []
    for path in _iter_files():
        rel = _rel(path)
        name_score = _score(rel.lower(), terms) * 3
        content_score = 0
        snippet = ""
        if path.suffix.lower() in TEXT_SUFFIXES:
            snippet, content_score = _text_match(path, terms)
        elif path.suffix.lower() == PDF_SUFFIX:
            snippet, content_score = _pdf_match(path, terms)
        score = name_score + content_score
        if score > 0:
            hits.append({"path": str(path), "label": rel, "score": score, "snippet": snippet})
    hits.sort(key=lambda hit: (-hit["score"], hit["label"].lower()))
    return hits[: max(1, min(int(limit), 50))]


def format_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matching local files found."
    lines = []
    for hit in hits:
        line = f"{hit['label']} ({hit['score']})"
        if hit.get("snippet"):
            line += f"\n  {hit['snippet']}"
        lines.append(line)
    return "\n".join(lines)


def _iter_files():
    seen: set[Path] = set()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path in seen or not path.is_file() or _skip(path):
                continue
            seen.add(path)
            yield path


def _skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & {".git", ".venv", "__pycache__", "build", "dist"})


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _score(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in text)


def _text_match(path: Path, terms: list[str]) -> tuple[str, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "", 0
    return _snippet_score(text, terms)


def _pdf_match(path: Path, terms: list[str]) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", 0
    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages[:10])
    except Exception:
        return "", 0
    return _snippet_score(text, terms)


def _snippet_score(text: str, terms: list[str]) -> tuple[str, int]:
    lowered = text.lower()
    score = _score(lowered, terms)
    if score == 0:
        return "", 0
    first = min((lowered.find(term) for term in terms if term in lowered), default=0)
    start = max(0, first - 60)
    snippet = " ".join(text[start : start + 180].split())
    return snippet, score
