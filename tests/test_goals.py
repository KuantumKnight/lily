from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lily import goals


class GoalEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(goals, "DB_PATH", Path(self.temp_dir.name) / "goals.db")
        self.timeline_patch = patch.object(goals.timeline, "append_event")
        self.bus_patch = patch.object(goals.bus, "publish")
        self.db_patch.start()
        self.timeline = self.timeline_patch.start()
        self.bus = self.bus_patch.start()

    def tearDown(self) -> None:
        self.bus_patch.stop()
        self.timeline_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_create_goal_is_active_and_records_provenance(self) -> None:
        goal = goals.create_goal(
            "Ship SentinelOS beta",
            outcome="Five people complete the daily loop",
            success_criteria="Three-day activation is measured",
            next_action="Implement the Goal Engine",
        )

        self.assertTrue(goal["active"])
        self.assertEqual(goal["status"], "active")
        self.assertEqual(goal["progress"], 0)
        self.assertEqual(goals.active_goal()["id"], goal["id"])
        event = goals.recent_events(goal["id"], 1)[0]
        self.assertEqual(event["kind"], "created")
        self.timeline.assert_called_once()
        self.bus.assert_called_with("goal.created", unittest.mock.ANY)

    def test_task_completion_drives_progress(self) -> None:
        goal = goals.create_goal("Build the daily loop")
        first = goals.add_task(goal["id"], "Create goal storage")
        goals.add_task(goal["id"], "Wire the dashboard")

        goals.update_task(goal["id"], first["id"], status="done")
        refreshed = goals.get_goal(goal["id"])

        self.assertEqual(refreshed["progress"], 50)
        self.assertEqual(refreshed["task_summary"], {
            "total": 2,
            "done": 1,
            "blocked": 0,
            "remaining": 1,
        })

    def test_only_one_goal_can_be_active(self) -> None:
        first = goals.create_goal("First goal")
        second = goals.create_goal("Second goal")

        self.assertFalse(goals.get_goal(first["id"])["active"])
        self.assertEqual(goals.active_goal()["id"], second["id"])

        goals.set_active(first["id"])
        self.assertEqual(goals.active_goal()["id"], first["id"])
        self.assertFalse(goals.get_goal(second["id"])["active"])

    def test_completed_goal_leaves_active_queue(self) -> None:
        goal = goals.create_goal("Complete me")

        completed = goals.update_goal(goal["id"], status="completed")

        self.assertEqual(completed["status"], "completed")
        self.assertFalse(completed["active"])
        self.assertIsNone(goals.active_goal())
        with self.assertRaisesRegex(ValueError, "cannot be activated"):
            goals.set_active(goal["id"])

    def test_invalid_status_is_rejected_without_mutation(self) -> None:
        goal = goals.create_goal("Stay valid")

        with self.assertRaisesRegex(ValueError, "invalid goal status"):
            goals.update_goal(goal["id"], status="imaginary")

        self.assertEqual(goals.get_goal(goal["id"])["status"], "active")

    def test_generated_tasks_are_deduplicated_and_set_next_action(self) -> None:
        goal = goals.create_goal("Plan this goal")
        goals.add_task(goal["id"], "Keep the existing task")

        result = goals.add_generated_tasks(
            goal["id"],
            [
                "Keep the existing task",
                "Write the implementation",
                "Run the tests",
                "run the tests",
            ],
        )

        self.assertEqual(
            [item["title"] for item in result["added"]],
            ["Write the implementation", "Run the tests"],
        )
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(result["goal"]["next_action"], "Write the implementation")
        self.assertEqual(result["goal"]["task_summary"]["total"], 3)
        self.bus.assert_called_with("goal.planned", unittest.mock.ANY)


if __name__ == "__main__":
    unittest.main()
