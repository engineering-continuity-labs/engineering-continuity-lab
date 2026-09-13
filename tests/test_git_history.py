from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from continuity.cli import main
from continuity.git.history import GitHistory


class GitHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Alice")
        self.git("config", "user.email", "alice@example.com")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.path), *args], stderr=subprocess.PIPE,
            env={**os.environ, "GIT_AUTHOR_DATE": "2025-01-01T12:00:00+00:00", "GIT_COMMITTER_DATE": "2025-01-01T12:00:00+00:00"})

    def save(self, message="change"):
        self.git("add", ".")
        self.git("commit", "-m", message)

    def test_numstat_binary_unusual_names_rename_and_delete(self):
        name = "tab\tnewline\nfile.txt"
        (self.path / name).write_text("one\ntwo\n")
        (self.path / "binary").write_bytes(b"\0abc")
        self.save("message\nCOMMIT\nnot a delimiter")
        history = GitHistory(self.path).read()
        changes = {c.path: c for c in history.commits[0].changes}
        self.assertEqual(changes[name].additions, 2)
        self.assertIsNone(changes["binary"].additions)
        self.assertEqual(history.commits[0].author.email, "alice@example.com")
        self.assertIsNotNone(history.commits[0].date.tzinfo)
        self.git("mv", name, "renamed")
        self.save()
        renamed = {c.path: c for c in GitHistory(self.path).read().commits[0].changes}
        self.assertEqual(renamed[name].deletions, 2)
        self.assertEqual(renamed["renamed"].additions, 2)
        (self.path / "renamed").unlink()
        self.save()
        self.assertEqual(GitHistory(self.path).read().commits[0].changes[0].deletions, 2)

    def test_merge_metadata_without_duplicate_diff(self):
        (self.path / "base").write_text("base")
        self.save()
        self.git("checkout", "-b", "side")
        (self.path / "side").write_text("side")
        self.save()
        self.git("checkout", "main")
        (self.path / "main").write_text("main")
        self.save()
        self.git("merge", "side", "--no-ff", "-m", "merge")
        history = GitHistory(self.path).read()
        self.assertEqual(len(history.commits), 4)
        self.assertEqual(history.commits[0].changes, ())
        self.assertEqual(sum(len(c.changes) for c in history.commits), 3)

    def test_mailmap_and_cli_views(self):
        (self.path / "a").write_text("a")
        self.save()
        (self.path / ".mailmap").write_text("Canonical <canonical@example.com> Alice <alice@example.com>\n")
        self.save()
        self.assertEqual(GitHistory(self.path).read().commits[-1].author.key, "canonical@example.com")
        for command in (["analyze"], ["person", "Canonical"], ["simulate-departure", "canonical@example.com"]):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([*command, "--repo", str(self.path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["commit_count"], 2)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["person", "", "--repo", str(self.path)]), 2)

    def test_empty_and_invalid_repository(self):
        with self.assertRaises(ValueError):
            GitHistory(self.path).read()
        with self.assertRaises(ValueError):
            GitHistory(self.path / "missing").read()

    def test_shallow_history_is_flagged(self):
        (self.path / "a").write_text("a")
        self.save()
        (self.path / "a").write_text("a\nb")
        self.save()
        with TemporaryDirectory() as destination:
            subprocess.run(["git", "clone", "--depth", "1", self.path.as_uri(), destination],
                           check=True, capture_output=True)
            history = GitHistory(Path(destination)).read()
            self.assertTrue(history.shallow)
            self.assertEqual(len(history.commits), 1)

    def test_invalid_config_is_friendly_error(self):
        for content in ('weights = 1', 'half_life_days = "slow"', 'unknown = 1'):
            config = self.path / "config.toml"
            config.write_text(content)
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main(["analyze", "--config", str(config)]), 2)
            self.assertTrue(errors.getvalue().startswith("continuity:"))

    def test_text_views_and_filter_audit(self):
        (self.path / "a.py").write_text("code")
        (self.path / "client.g.cs").write_text("generated")
        self.save()
        for command in (["analyze"], ["person", "Alice"], ["simulate-departure", "Alice"]):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([*command, "--repo", str(self.path), "--format", "text", "--exclude-generated"]), 0)
            text = output.getvalue()
            self.assertIn("1 retained / 2 total; 1 excluded", text)
            self.assertIn("CRITICAL" if command[0] != "simulate-departure" else "100.0%", text)
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["analyze", "--repo", str(self.path), "--exclude-generated"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data['filter_evidence']['excluded_paths'], ['client.g.cs'])
        self.assertTrue(data['filters']['exclude_generated'])
        self.assertEqual(data['components'][0]['contributors'][0]['files'], ['a.py'])
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["analyze", "--repo", str(self.path), "--exclude-path", "*", "--format", "text"]), 0)
        self.assertIn("no risk classification", output.getvalue())
