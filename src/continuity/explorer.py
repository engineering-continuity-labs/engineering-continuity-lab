"""Loopback-only server that connects the local browser explorer to Git analysis."""
from dataclasses import asdict
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
from socketserver import BaseServer
from typing import Any, cast

from continuity.analysis.filtering import FilterConfig, filter_history
from continuity.analysis.service import analyze
from continuity.domain.models import DirectoryComponents
from continuity.git.history import GitHistory
from continuity.git.source import resolve_repository
from continuity.scoring.model import ScoringConfig

STATIC_DIRECTORY = Path(__file__).resolve().parents[2] / "ui" / "dist"
MAX_REQUEST_BYTES = 64 * 1024


def analysis_output(repository: str) -> dict[str, Any]:
    """Produce the unchanged `analyze` JSON schema for one local repository."""
    config = ScoringConfig()
    filters = FilterConfig()
    with resolve_repository(repository) as workspace:
        history, evidence = filter_history(GitHistory(workspace.path).read(), filters)
        report = analyze(history, DirectoryComponents(), config)
        output = {
        "model": "experimental-v0.1",
        "warning": "Git activity is only a proxy for knowledge.",
        "configuration": {"weights": dict(config.weights), "half_life_days": config.half_life_days, "component_depth": 1},
        "filters": asdict(filters),
        "filter_evidence": asdict(evidence),
        "revision": report.revision,
        "as_of": report.as_of.isoformat(),
        "shallow": report.shallow,
        "commit_count": report.commit_count,
            "components": [asdict(component) for component in report.components],
        }
        if workspace.source is not None:
            output["source"] = workspace.source
        return output


class ExplorerHandler(SimpleHTTPRequestHandler):
    """Serve static files and a narrowly scoped same-origin analysis endpoint."""

    def __init__(self, request: socket.socket, client_address: tuple[str, int], server: BaseServer) -> None:
        super().__init__(request, client_address, server, directory=str(STATIC_DIRECTORY))

    def end_headers(self) -> None:
        """Keep the local explorer's static files current during a local session."""
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.send_json(HTTPStatus.OK, {"local": True})
            return
        if self.path.startswith("/api/"):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "unknown local API path"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/analyze":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "unknown local API path"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
            if length < 1 or length > MAX_REQUEST_BYTES:
                raise ValueError("request body must be between 1 and 65536 bytes")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or not isinstance(payload.get("repository"), str):
                raise ValueError("repository must be a local path string")
            repository_path = payload["repository"].strip()
            if not repository_path:
                raise ValueError("repository path cannot be empty")
            self.send_json(HTTPStatus.OK, analysis_output(repository_path))
        except (ValueError, OSError, TypeError, OverflowError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        return


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return ThreadingHTTPServer(("127.0.0.1", port), ExplorerHandler)


def serve(port: int = 8765) -> None:
    server = make_server(port)
    host, actual_port = cast(tuple[str, int], server.server_address)
    print(f"Engineering Continuity Lab explorer: http://{host}:{actual_port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
