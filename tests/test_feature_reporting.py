import json
import os
import subprocess
import sys
from contextlib import chdir
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, call, patch

import allure
from behave.configuration import Configuration
from behave.model_type import Status
from playwright.sync_api import Page

from features import environment


class FeatureReportingTest(TestCase):
    def setUp(self):
        self.tmp_path = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(chdir(self.tmp_path))
        self.enterContext(patch.object(environment, "__file__", str(self.tmp_path / "features" / "environment.py")))
        self.enterContext(patch.dict(os.environ))
        for name in ("SSO_MODE", "FEATURE_TEST_BRANCH", "FEATURE_TEST_COMMIT", "FEATURE_TEST_ARGS"):
            os.environ.pop(name, None)

    def test_report_environment_uses_selected_allure_output(self):
        results = self.tmp_path / "custom-results"
        config = Configuration(
            ["-f", "plain", "-f", "allure_behave.formatter:AllureFormatter", "-o", "-", "-o", str(results)]
        )
        config.userdata["base_url"] = "http://web:8000"
        os.environ.update(
            SSO_MODE="one-login",
            FEATURE_TEST_BRANCH="test/CS-788-generate-html-report",
            FEATURE_TEST_COMMIT="abc123",
            FEATURE_TEST_ARGS="--tags=~dex -i admin-login.feature",
        )

        environment.write_report_environment(config)

        properties = (results / "environment.properties").read_text()
        self.assertIn("Environment=one-login\n", properties)
        self.assertIn("Base\\ URL=http://web:8000\n", properties)
        self.assertIn("Branch=test/CS-788-generate-html-report\n", properties)
        self.assertIn("Commit\\ SHA=abc123\n", properties)
        self.assertIn("Feature/tag\\ filter=--tags=~dex -i admin-login.feature\n", properties)
        started_at = next(line.split("=", 1)[1] for line in properties.splitlines() if line.startswith("Started"))
        self.assertEqual(datetime.fromisoformat(started_at).utcoffset().total_seconds(), 0)

    def test_report_environment_defaults_and_escapes_values(self):
        config = Configuration(["-f", "allure_behave.formatter:AllureFormatter", "-o", str(self.tmp_path)])
        config.userdata.clear()
        os.environ["FEATURE_TEST_BRANCH"] = "branch\\name\nInjected=value\r"

        environment.write_report_environment(config)

        properties = (self.tmp_path / "environment.properties").read_text()
        self.assertIn("Environment=unknown\n", properties)
        self.assertIn("Base\\ URL=unknown\n", properties)
        self.assertIn("Commit\\ SHA=unknown\n", properties)
        self.assertIn("Feature/tag\\ filter=(none)\n", properties)
        self.assertIn("Branch=branch\\\\name\\nInjected=value\\r\n", properties)

    def test_non_allure_run_does_not_write_metadata(self):
        config = Configuration(["-f", "plain", "-o", str(self.tmp_path / "plain.txt")])

        environment.write_report_environment(config)

        self.assertFalse((self.tmp_path / "plain.txt").exists())

    def test_failed_scenario_saves_and_attaches_screenshot_and_html(self):
        for status in (Status.failed, Status.error):
            with self.subTest(status=status):
                page = Mock(spec=Page)
                page.screenshot.return_value = b"screenshot"
                page.content.return_value = "<html><body>Failure evidence</body></html>"
                scenario = SimpleNamespace(
                    status=status, name="Failure / unsafe: name?", filename="features/report.feature", line=10
                )

                with patch.object(environment.allure, "attach") as attach:
                    environment.after_scenario(SimpleNamespace(page=page), scenario)

                page.screenshot.assert_called_once()
                screenshot_path = Path(page.screenshot.call_args.kwargs["path"])
                self.assertEqual(page.screenshot.call_args.kwargs["full_page"], True)
                self.assertRegex(screenshot_path.name, r"^Failure_unsafe_name_[a-f0-9]{16}\.png$")
                self.assertEqual(screenshot_path.with_suffix(".html").read_text(), page.content.return_value)
                page.content.assert_called_once()
                self.assertEqual(
                    attach.call_args_list,
                    [
                        call(b"screenshot", name="Screenshot", attachment_type=allure.attachment_type.PNG),
                        call(page.content.return_value, name="Page HTML", attachment_type=allure.attachment_type.HTML),
                    ],
                )

    def test_failure_artifacts_do_not_overwrite_other_scenarios(self):
        scenarios = [
            ("Failure/A", "features/report.feature", 10),
            ("Failure?A", "features/report.feature", 10),
            ("Failure/A", "features/other.feature", 10),
            ("Failure/A", "features/report.feature", 20),
        ]
        page = Mock(spec=Page)

        def save_screenshot(path, full_page):
            screenshot = page.screenshot.return_value
            Path(path).write_bytes(screenshot)
            return screenshot

        page.screenshot.side_effect = save_screenshot
        artifact_paths = []
        with patch.object(environment.allure, "attach"):
            for index, (name, filename, line) in enumerate(scenarios):
                page.screenshot.return_value = f"Screenshot {index}".encode()
                page.content.return_value = f"<html>Failure {index}</html>"
                scenario = SimpleNamespace(status=Status.failed, name=name, filename=filename, line=line)

                environment.after_scenario(SimpleNamespace(page=page), scenario)

                artifact_paths.append(Path(page.screenshot.call_args.kwargs["path"]))

        self.assertEqual(len(set(artifact_paths)), len(scenarios))
        for index, screenshot_path in enumerate(artifact_paths):
            self.assertEqual(screenshot_path.read_bytes(), f"Screenshot {index}".encode())
            self.assertEqual(screenshot_path.with_suffix(".html").read_text(), f"<html>Failure {index}</html>")

    def test_failure_artifact_names_are_stable(self):
        page = Mock(spec=Page)
        page.screenshot.return_value = b"screenshot"
        page.content.return_value = "<html>Failure evidence</html>"
        scenario = SimpleNamespace(status=Status.failed, name="Failure/A", filename="features/report.feature", line=10)

        with patch.object(environment.allure, "attach"):
            environment.after_scenario(SimpleNamespace(page=page), scenario)
            environment.after_scenario(SimpleNamespace(page=page), scenario)

        first, second = page.screenshot.call_args_list
        self.assertEqual(first.kwargs["path"], second.kwargs["path"])

    def test_successful_or_skipped_scenario_does_not_capture_artifacts(self):
        for status in (Status.passed, Status.skipped):
            with self.subTest(status=status):
                page = Mock(spec=Page)

                with patch.object(environment.allure, "attach") as attach:
                    environment.after_scenario(SimpleNamespace(page=page), SimpleNamespace(status=status))

                page.screenshot.assert_not_called()
                page.content.assert_not_called()
                attach.assert_not_called()

    def test_failed_scenario_without_page_does_not_attach(self):
        with patch.object(environment.allure, "attach") as attach:
            environment.after_scenario(SimpleNamespace(), SimpleNamespace(status=Status.failed, name="Startup failure"))

        attach.assert_not_called()

    def test_behave_report_contains_failure_details_and_both_attachments(self):
        """Exercise the real formatter and hooks without the application or a browser."""
        features = self.tmp_path / "features"
        steps = features / "steps"
        steps.mkdir(parents=True)
        (self.tmp_path / "artifacts").mkdir()
        (features / "report.feature").write_text(
            "Feature: Reporting\n"
            "  Scenario: Passing scenario\n"
            "    Given a passing step\n"
            "  Scenario: Failing scenario\n"
            "    Given a failing step\n"
            "    Then a passing step\n"
        )
        (steps / "steps.py").write_text(
            "from behave import given, then\n"
            "@given('a passing step')\n"
            "@then('a passing step')\n"
            "def passing(context): pass\n"
            "@given('a failing step')\n"
            "def failing(context): raise AssertionError('Expected reporting failure')\n"
        )
        (features / "environment.py").write_text(
            "from unittest.mock import Mock\n"
            "from playwright.sync_api import Page\n"
            "from features import environment as hooks\n"
            "hooks.__file__ = __file__\n"
            "after_scenario = hooks.after_scenario\n"
            "def before_all(context):\n"
            "    hooks.write_report_environment(context.config)\n"
            "    context.page = Mock(spec=Page)\n"
            "    context.page.screenshot.return_value = b'screenshot'\n"
            "    context.page.content.return_value = '<html>Failure evidence</html>'\n"
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "behave",
                str(features),
                "-f",
                "allure_behave.formatter:AllureFormatter",
                "-o",
                "results",
            ],
            cwd=self.tmp_path,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        results = [json.loads(path.read_text()) for path in (self.tmp_path / "results").glob("*-result.json")]
        self.assertEqual(len(results), 2)
        results = {item["name"]: item for item in results}
        self.assertEqual(results["Passing scenario"]["status"], "passed")
        failing = results["Failing scenario"]
        self.assertEqual(failing["status"], "failed")
        self.assertIn("Expected reporting failure", failing["statusDetails"]["message"])
        self.assertIn('File "', failing["statusDetails"]["trace"])
        self.assertIn("steps.py", failing["statusDetails"]["trace"])
        self.assertEqual([step["status"] for step in failing["steps"]], ["failed", "skipped"])
        self.assertGreaterEqual(failing["stop"], failing["start"])
        attachments = {item["name"]: item for item in failing["attachments"]}
        self.assertEqual(attachments["Screenshot"]["type"], "image/png")
        self.assertEqual(attachments["Page HTML"]["type"], "text/html")
        self.assertEqual(
            (self.tmp_path / "results" / attachments["Page HTML"]["source"]).read_text(),
            "<html>Failure evidence</html>",
        )
        self.assertTrue((self.tmp_path / "results" / "environment.properties").exists())
