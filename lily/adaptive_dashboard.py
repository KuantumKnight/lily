"""Adaptive dashboard card selection."""

ALWAYS_ON = {"status", "profile", "goal", "system", "timeline", "agents"}


def select(cards: dict) -> dict:
    """Return only dashboard cards that are currently useful."""
    selected = {key: value for key, value in cards.items() if key in ALWAYS_ON}

    habits = cards.get("habits") or {}
    if habits.get("summary") or habits.get("work_hours") or habits.get("busiest_weekday"):
        selected["habits"] = habits

    facts = cards.get("facts") or {}
    if facts.get("facts"):
        selected["facts"] = facts

    projects = cards.get("projects") or {}
    if projects.get("active") or projects.get("projects"):
        selected["projects"] = projects

    return selected
