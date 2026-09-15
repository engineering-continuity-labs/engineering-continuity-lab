from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from continuity.cli import main
from continuity.git.history import GitHistory
from continuity.git.source import resolve_repository


class RepositorySourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.origin = Path(self.temp.name) / "origin"
        self.origin.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Alice")
        self.git("config", "user.email", "alice@example.com")
        (self.origin / "module.py").write_text("one\n")
        self.git("add", ".")
        self.git("commit", "-m", "first")
        (self.origin / "module.py").write_text("one\ntwo\n")
        self.git("commit", "-am", "second")
        self.real_run = subprocess.run
        self.clone_commands: list[list[str]] = []

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.origin), *args], check=True, capture_output=True,
            env={**os.environ, "GIT_AUTHOR_DATE": "2025-01-01T12:00:00+00:00",
                 "GIT_COMMITTER_DATE": "2025-01-01T12:00:00+00:00"},
        )

    def clone_as_local_origin(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.clone_commands.append(command)
        if command[:3] == ["git", "clone", "--"]:
            return self.real_run(
                ["git", "clone", str(self.origin), command[-1]], capture_output=True, text=True, check=False
            )
        return self.real_run(command, **kwargs)

    def test_remote_workspace_uses_full_clone_and_cleans_up(self) -> None:
        with patch("continuity.git.source.subprocess.run", side_effect=self.clone_as_local_origin):
            with resolve_repository("https://example.test/project.git") as workspace:
                clone_path = workspace.path
                self.assertEqual(workspace.source, "https://example.test/project.git")
                self.assertEqual(len(GitHistory(clone_path).read().commits), 2)
                self.assertTrue(clone_path.exists())
        self.assertFalse(clone_path.exists())
        self.assertEqual(self.clone_commands[0][:3], ["git", "clone", "--"])
        self.assertNotIn("--depth", self.clone_commands[0])

    def test_remote_workspace_cleans_up_after_analysis_failure(self) -> None:
        with patch("continuity.git.source.subprocess.run", side_effect=self.clone_as_local_origin):
            with self.assertRaises(RuntimeError):
                with resolve_repository("https://example.test/project.git") as workspace:
                    clone_path = workspace.path
                    raise RuntimeError("analysis failed")
        self.assertFalse(clone_path.exists())

    def test_rejects_unsupported_and_credentialed_urls(self) -> None:
        for source in ("ssh://example.test/project.git", "git@example.test:project.git", "file:///tmp/project", "ftp://example.test/project", "https://user:secret@example.test/project.git"):
            with self.assertRaises(ValueError):
                resolve_repository(source)

    def test_clone_failure_is_clear_and_does_not_leak_workspace(self) -> None:
        result = subprocess.CompletedProcess(["git", "clone"], 128, "", "fatal: /tmp/continuity-secret/repository")
        with patch("continuity.git.source.subprocess.run", return_value=result):
            with self.assertRaisesRegex(ValueError, "unable to clone repository") as error:
                resolve_repository("https://example.test/project.git")
        self.assertNotIn("continuity-secret", str(error.exception))

    def test_cli_remote_source_applies_to_every_view_and_keeps_json_clean(self) -> None:
        with patch("continuity.git.source.subprocess.run", side_effect=self.clone_as_local_origin):
            for command in (["analyze"], ["person", "Alice"], ["simulate-departure", "Alice"]):
                output, errors = io.StringIO(), io.StringIO()
                with redirect_stdout(output), redirect_stderr(errors):
                    self.assertEqual(main([*command, "--repo", "https://example.test/project.git"]), 0)
                report = json.loads(output.getvalue())
                self.assertEqual(report["source"], "https://example.test/project.git")
                self.assertIn("Cloning repository...", errors.getvalue())
                self.assertIn("Reading Git history...", errors.getvalue())
                self.assertIn("Analyzing evidence...", errors.getvalue())
                self.assertNotIn("continuity-", output.getvalue())

    def test_interactive_https_url_uses_same_resolution(self) -> None:
        class InteractiveInput(io.StringIO):
            def isatty(self) -> bool:
                return True

        with patch("continuity.git.source.subprocess.run", side_effect=self.clone_as_local_origin), \
             patch("sys.stdin", InteractiveInput()), \
             patch("builtins.input", return_value=" https://example.test/project.git ") as prompt, \
             redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
            self.assertEqual(main(["analyze"]), 0)
        self.assertIn("Engineering Continuity Lab", output.getvalue())
        self.assertIn("Repository path or clone URL", prompt.call_args.args[0])
