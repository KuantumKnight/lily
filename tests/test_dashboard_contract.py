from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "lily" / "dashboard_static"
DASHBOARD_SOURCE = ROOT / "lily" / "dashboard.py"
ADAPTIVE_SOURCE = ROOT / "lily" / "adaptive_dashboard.py"


class DashboardContractTests(unittest.TestCase):
    def test_chat_assets_and_routes_exist(self) -> None:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        source = DASHBOARD_SOURCE.read_text(encoding="utf-8")

        self.assertIn('id="chat-form"', html)
        self.assertIn('id="messages"', html)
        self.assertIn('fetch("/api/chat"', script)
        self.assertIn('@app.post("/api/chat")', source)
        self.assertIn('@app.get("/api/chat/history")', source)

    def test_operating_layer_cards_exist(self) -> None:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        source = DASHBOARD_SOURCE.read_text(encoding="utf-8")
        adaptive = ADAPTIVE_SOURCE.read_text(encoding="utf-8")

        for card_id in ("card-goal", "card-profile", "card-timeline", "card-agents"):
            self.assertIn(f'id="{card_id}"', html)

        for renderer in ("renderGoal", "renderProfile", "renderTimeline", "renderAgents"):
            self.assertIn(f"function {renderer}", script)

        for provider in ("goal_card", "profile_card", "timeline_card", "agents_card"):
            self.assertIn(f"def {provider}", source)

        for card_name in ('"goal"', '"profile"', '"timeline"', '"agents"'):
            self.assertIn(card_name, adaptive)

    def test_goal_engine_controls_and_routes_exist(self) -> None:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        source = DASHBOARD_SOURCE.read_text(encoding="utf-8")

        for element_id in ("goal-dialog", "goal-form", "new-goal"):
            self.assertIn(f'id="{element_id}"', html)
        for action in (
            "data-goal-status",
            "data-task-toggle",
            "data-goal-activate",
            "data-goal-plan",
        ):
            self.assertIn(action, script)
        for route in ('@app.post("/api/goals")', '@app.patch("/api/goals/{goal_id}")',
                      '@app.post("/api/goals/{goal_id}/tasks")',
                      '@app.post("/api/goals/{goal_id}/plan")'):
            self.assertIn(route, source)

    def test_static_assets_are_present(self) -> None:
        for name in ("index.html", "app.js", "card.js", "style.css"):
            path = STATIC_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100, name)


if __name__ == "__main__":
    unittest.main()
