from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "lily" / "dashboard_static"
DASHBOARD_SOURCE = ROOT / "lily" / "dashboard.py"

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

    def test_static_assets_are_present(self) -> None:
        for name in ("index.html", "app.js", "card.js", "style.css"):
            path = STATIC_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100, name)


if __name__ == "__main__":
    unittest.main()
