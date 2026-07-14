from __future__ import annotations

import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout

from lily import doctor


class DoctorTests(unittest.TestCase):
    def test_load_settings_honors_file_and_environment_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "lily.toml"
            config.write_text(
                '[lily]\nmodel = "from-file"\ndashboard_port = 8123\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"LILY_MODEL": "from-env"}, clear=False):
                settings = doctor.load_settings(root)

        self.assertEqual(settings.model, "from-env")
        self.assertEqual(settings.dashboard_port, 8123)
        self.assertFalse(settings.config_error)

    def test_invalid_toml_is_reported_as_a_failed_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lily.toml").write_text("[lily\nmodel = broken", encoding="utf-8")
            settings = doctor.load_settings(root)

        checks = doctor._config_checks(settings)
        self.assertEqual(checks[0].status, "fail")
        self.assertIn("Cannot use", checks[0].detail)

    def test_remote_dashboard_binding_is_rejected(self) -> None:
        settings = doctor.Settings(
            config_path=Path("lily.toml"),
            config_error="",
            model="qwen3:8b",
            embed_model="nomic-embed-text",
            vision_model="llava:7b",
            ollama_host="http://localhost:11434",
            dashboard_host="0.0.0.0",
            dashboard_port=8000,
            tts_voice="",
        )

        checks = doctor._config_checks(settings)

        self.assertTrue(any(check.name == "Dashboard binding" and check.status == "fail" for check in checks))

    def test_model_checks_distinguish_required_and_optional_models(self) -> None:
        settings = doctor.load_settings(Path("missing-root"))
        payload = json.dumps({"models": [{"name": settings.embed_model}]}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return payload

        with (
            patch.object(doctor.shutil, "which", return_value="ollama.exe"),
            patch.object(doctor.urllib.request, "urlopen", return_value=Response()),
        ):
            checks = doctor._ollama_checks(settings, timeout=0.1)

        by_name = {check.name: check for check in checks}
        self.assertEqual(by_name["Ollama service"].status, "pass")
        self.assertEqual(by_name["Chat model"].status, "fail")
        self.assertEqual(by_name["Embedding model"].status, "pass")
        self.assertEqual(by_name["Vision model"].status, "warn")

    def test_text_summary_and_exit_code_reflect_failures(self) -> None:
        checks = [
            doctor.Check("pass", "Python", "ready"),
            doctor.Check("fail", "Chat model", "missing", "pull it"),
        ]
        rendered = doctor._render_text(checks)

        self.assertIn("1 passed, 0 warnings, 1 failed", rendered)
        self.assertIn("Fix: pull it", rendered)
        with (
            patch.object(doctor, "run_checks", return_value=checks),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(doctor.main([]), 1)


if __name__ == "__main__":
    unittest.main()
