from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lily import chat, memory


class ChatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(memory, "DB_PATH", Path(self.temp_dir.name) / "test.db")
        self.db_patch.start()

    def tearDown(self) -> None:
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_build_context_persists_trimmed_user_turn(self) -> None:
        messages = chat.build_context("  help me plan today  ")

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1], {"role": "user", "content": "help me plan today"})
        self.assertEqual(memory.recent(1), [{"role": "user", "content": "help me plan today"}])

    def test_build_context_includes_memory_and_active_project(self) -> None:
        memory.remember_fact("Prefers concise answers", "preference")
        memory.set_active_project("Sentinal")
        memory.add_project_note("Sentinal", "Ship the desktop chat first")

        messages = chat.build_context("what next?")

        system = messages[0]["content"]
        self.assertIn("Prefers concise answers", system)
        self.assertIn("Active project: Sentinal", system)
        self.assertIn("Ship the desktop chat first", system)

    def test_respond_persists_assistant_reply(self) -> None:
        with (
            patch.object(chat, "prepare"),
            patch.object(chat.orchestrator, "handle", return_value="Start with the release gate") as handle,
        ):
            reply = chat.respond("what should I do?")

        self.assertEqual(reply, "Start with the release gate")
        self.assertEqual(
            memory.recent(2),
            [
                {"role": "user", "content": "what should I do?"},
                {"role": "assistant", "content": "Start with the release gate"},
            ],
        )
        handle.assert_called_once()

    def test_empty_message_is_rejected_without_writing_memory(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            chat.build_context("   ")
        self.assertEqual(memory.recent(10), [])


if __name__ == "__main__":
    unittest.main()
