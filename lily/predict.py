"""Predictive assistance from local patterns."""

from collections import Counter

from . import memory, timeline


def suggestions(limit: int = 5) -> list[str]:
    """Suggest likely next actions from local history and current project state."""
    limit = max(1, min(int(limit), 20))
    candidates: list[str] = []

    project = memory.active_project()
    if project:
        candidates.append(f"Review recent notes for active project '{project}'.")

    for event in timeline.recent(80):
        text = (event.get("content") or event.get("title") or "").strip()
        suggestion = _suggest_from_text(text)
        if suggestion:
            candidates.append(suggestion)

    ranked = Counter(candidates).most_common(limit)
    return [item for item, _ in ranked]


def format_suggestions(limit: int = 5) -> str:
    items = suggestions(limit)
    if not items:
        return "No predictive suggestions yet; Lily needs more local history."
    return "Likely next steps:\n" + "\n".join(f"- {item}" for item in items)


def _suggest_from_text(text: str) -> str:
    lowered = text.lower()
    if "run tests" in lowered or "tests failed" in lowered:
        return "Run the test suite again after the next code change."
    if "commit" in lowered or "push" in lowered:
        return "Check git status before the next commit."
    if "reminder" in lowered:
        return "Review pending reminders."
    if "calendar" in lowered:
        return "Check upcoming calendar conflicts."
    if "security" in lowered or "secret" in lowered:
        return "Run a quick secret scan before sharing changes."
    if "screenshot" in lowered or "ocr" in lowered:
        return "Capture or OCR the screen if visual context changed."
    return ""
