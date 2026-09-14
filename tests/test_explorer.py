from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from continuity.cli import main
from continuity.explorer import make_server


class ExplorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repository = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Alice")
        self.git("config", "user.email", "alice@example.com")
        (self.repository / "module.py").write_text("print('hello')\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repository), *args],
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_DATE": "2025-01-01T12:00:00+00:00",
                "GIT_COMMITTER_DATE": "2025-01-01T12:00:00+00:00",
            },
        )

    def start_server(self) -> int:
        server = make_server(0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop_server() -> None:
            server.shutdown()
            thread.join()
            server.server_close()

        self.addCleanup(stop_server)
        return server.server_address[1]

    def request(self, port: int, method: str, path: str, body: object | None = None) -> tuple[int, object, str | None]:
        connection = HTTPConnection("127.0.0.1", port, timeout=5)
        encoded = json.dumps(body) if body is not None else None
        connection.request(method, path, encoded, {"Content-Type": "application/json"})
        response = connection.getresponse()
        result = (response.status, json.loads(response.read()), response.getheader("Cache-Control"))
        connection.close()
        return result

    def test_loopback_server_serves_static_ui_and_analyzes_local_repository(self) -> None:
        port = self.start_server()
        separate_server = make_server(0)
        self.addCleanup(separate_server.server_close)
        self.assertEqual(separate_server.server_address[0], "127.0.0.1")
        status, health, cache_control = self.request(port, "GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health, {"local": True})
        self.assertEqual(cache_control, "no-store")
        status, report, _ = self.request(port, "POST", "/api/analyze", {"repository": f"  {self.repository}  "})
        self.assertEqual(status, 200)
        self.assertIsInstance(report, dict)
        self.assertEqual(report["commit_count"], 1)
        self.assertEqual(report["model"], "experimental-v0.1")
        self.assertTrue(report["components"])

    def test_explorer_rejects_empty_and_invalid_requests(self) -> None:
        port = self.start_server()
        for body in ({"repository": "   "}, {"repository": str(self.repository / "missing")}, {}):
            status, response, _ = self.request(port, "POST", "/api/analyze", body)
            self.assertEqual(status, 400)
            self.assertIsInstance(response, dict)
            self.assertIn("error", response)
        status, response, _ = self.request(port, "POST", "/api/unknown", {})
        self.assertEqual(status, 404)
        self.assertEqual(response, {"error": "unknown local API path"})

    def test_cli_explorer_command_dispatches_to_local_server(self) -> None:
        with patch("continuity.explorer.serve") as serve:
            self.assertEqual(main(["explorer", "--port", "8766"]), 0)
        serve.assert_called_once_with(8766)
