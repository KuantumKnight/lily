from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - optional dashboard dependency
    TestClient = None

from lily import dashboard


@unittest.skipIf(TestClient is None, "FastAPI test client is not installed")
class DashboardGoalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "dashboard.db"
        self.goal_db_patch = patch.object(dashboard.goals, "DB_PATH", db_path)
        self.memory_db_patch = patch.object(dashboard.memory, "DB_PATH", db_path)
        self.timeline_patch = patch.object(dashboard.goals.timeline, "append_event")
        self.goal_db_patch.start()
        self.memory_db_patch.start()
        self.timeline_patch.start()
        self.client = TestClient(dashboard.create_app())

    def tearDown(self) -> None:
        self.client.close()
        self.timeline_patch.stop()
        self.memory_db_patch.stop()
        self.goal_db_patch.stop()
        self.temp_dir.cleanup()

    def test_goal_lifecycle_through_dashboard_api(self) -> None:
        created = self.client.post(
            "/api/goals",
            json={
                "title": "Ship the daily loop",
                "outcome": "One complete workflow works without chat",
                "next_action": "Add the first task",
                "priority": 2,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        goal = created.json()

        task_response = self.client.post(
            f"/api/goals/{goal['id']}/tasks",
            json={"title": "Verify task-derived progress"},
        )
        self.assertEqual(task_response.status_code, 200, task_response.text)
        task = task_response.json()

        completed_task = self.client.patch(
            f"/api/goals/{goal['id']}/tasks/{task['id']}",
            json={"status": "done"},
        )
        self.assertEqual(completed_task.status_code, 200, completed_task.text)

        refreshed = self.client.get(f"/api/goals/{goal['id']}")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(refreshed.json()["progress"], 100)

        completed_goal = self.client.patch(
            f"/api/goals/{goal['id']}",
            json={"status": "completed"},
        )
        self.assertEqual(completed_goal.status_code, 200, completed_goal.text)
        self.assertFalse(completed_goal.json()["active"])

    def test_planner_turns_goal_context_into_persisted_tasks(self) -> None:
        created = self.client.post(
            "/api/goals",
            json={
                "title": "Ship task generation",
                "outcome": "The dashboard can generate an execution plan",
                "success_criteria": "Generated tasks persist and render",
            },
        ).json()

        with patch.object(
            dashboard.planner_agent,
            "plan",
            return_value=["Add the endpoint", "Wire the button", "Run the tests"],
        ) as plan:
            response = self.client.post(f"/api/goals/{created['id']}/plan")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["added"]), 3)
        self.assertEqual(payload["goal"]["next_action"], "Add the endpoint")
        self.assertEqual(payload["goal"]["task_summary"]["total"], 3)
        prompt = plan.call_args.args[0]
        self.assertIn("Ship task generation", prompt)
        self.assertIn("Generated tasks persist and render", prompt)


if __name__ == "__main__":
    unittest.main()
