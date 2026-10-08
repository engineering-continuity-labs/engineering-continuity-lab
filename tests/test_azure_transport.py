"""SYNTHETIC transport isolation/privacy checks; no real PAT or network account."""
import base64
from dataclasses import asdict, replace
from email.message import Message
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import pickle
import ssl
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from azure_rest_fixture import STAMP, IDENTITIES, REPOSITORY, RestFixture, profile
from continuity.analysis.traceability import derive
from continuity.reporting.traceability import traceability_to_json
from continuity.traceability_providers.azure_devops import AzureDevOpsTraceabilityProvider, AzureLimits
from continuity.traceability_providers.azure_transport import AzureHttpTransport, AzureTransportError

SECRET = "PAT_SENTINEL_SYNTHETIC_NOT_A_CREDENTIAL"
RAW = "RAW_BODY_SENTINEL_SYNTHETIC"


class Response:
    def __init__(self, raw=b'{"value": []}', headers=None, status=200):
        self.raw = raw
        self.headers = headers or {}
        self.status = status
        self.read_sizes = []

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size):
        self.read_sizes.append(size)
        return self.raw[:size]


class Opener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if isinstance(self.response, Exception): raise self.response
        return self.response


class AzureTransportTests(unittest.TestCase):
    def test_runtime_auth_header_timeout_and_verified_tls(self):
        configured = profile()
        opener = Opener(Response(headers={"Set-Cookie": SECRET, "x-ms-continuationtoken": "SYNTHETIC-next"}))
        captured = []
        def build(*handlers):
            captured.extend(handlers)
            return opener
        transport = AzureHttpTransport(configured, SECRET)
        with patch("continuity.traceability_providers.azure_transport.build_opener", side_effect=build):
            response = transport.request(("git", "repositories", REPOSITORY, "pullrequests"), {})
        request, timeout = opener.calls[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Basic " + base64.b64encode((":" + SECRET).encode()).decode())
        self.assertEqual(timeout, configured.limits.timeout)
        self.assertNotIn(SECRET, request.full_url)
        self.assertIsNone(request.get_header("Cookie"))
        self.assertEqual(response.continuation, "SYNTHETIC-next")
        self.assertNotIn(SECRET, repr(response))
        https = next(h for h in captured if type(h).__name__ == "HTTPSHandler")
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(next(h for h in captured if type(h).__name__ == "ProxyHandler").proxies, {})
        self.assertNotIn(SECRET, repr(transport))
        with self.assertRaises(TypeError): pickle.dumps(transport)
        with self.assertRaises(TypeError): asdict(transport)

    def test_anonymous_get_and_wiql_is_the_only_post(self):
        opener = Opener(Response())
        transport = AzureHttpTransport(profile())
        with patch("continuity.traceability_providers.azure_transport.build_opener", return_value=opener):
            transport.request(("wit", "workitems"), {"ids": "1001"})
            transport.request(("wit", "wiql"), {}, {"query": "SELECT [System.Id] FROM WorkItems"})
        self.assertIsNone(opener.calls[0][0].get_header("Authorization"))
        self.assertEqual(opener.calls[1][0].get_method(), "POST")
        self.assertEqual(json.loads(opener.calls[1][0].data), {"query": "SELECT [System.Id] FROM WorkItems"})
        for endpoint, body in ((("wit", "workitems"), {}), (("wit", "wiql"), None),
                               (("wit", "workitems", "1001"), None), (("git", "repositories", "foreign", "commits"), None),
                               (("https://foreign.invalid",), None), (("..", "wit", "wiql"), None)):
            with self.subTest(endpoint=endpoint), self.assertRaises(AzureTransportError):
                transport.request(endpoint, {}, body)

    def assert_sanitized(self, error):
        self.assertNotIn(SECRET, str(error))
        self.assertNotIn(RAW, str(error))
        self.assertNotIn("synthetic.invalid", str(error))
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)

    def test_http_failures_are_categorical_no_body_or_exception_context(self):
        for code in (301, 302, 307, 308, 400, 401, 403, 404, 405, 429, 500, 501, 503):
            body = BytesIO((RAW + SECRET).encode())
            error = HTTPError("https://synthetic.invalid/" + SECRET, code, RAW + SECRET, Message(), body)
            opener = Opener(error)
            with patch("continuity.traceability_providers.azure_transport.build_opener", return_value=opener):
                try:
                    AzureHttpTransport(profile(), SECRET).request(("wit", "workitems"), {})
                except AzureTransportError as safe:
                    self.assert_sanitized(safe)
                    self.assertEqual(safe.unsupported, code in (405, 501))
                else: self.fail("expected sanitized HTTP failure")
            self.assertTrue(body.closed)

    def test_network_timeout_tls_and_incomplete_read_errors_are_sanitized(self):
        for raw_error in (URLError(SECRET + RAW), TimeoutError(SECRET + RAW), ssl.SSLCertVerificationError(SECRET),
                          IncompleteRead((SECRET + RAW).encode(), 123)):
            with patch("continuity.traceability_providers.azure_transport.build_opener", return_value=Opener(raw_error)):
                try:
                    AzureHttpTransport(profile(), SECRET).request(("wit", "workitems"), {})
                except AzureTransportError as error:
                    self.assert_sanitized(error)
                else: self.fail("expected sanitized transport failure")

    def test_strict_bounded_json_decode(self):
        invalid = [b'{"value": [], "value": []}', b'{"value": NaN}', b'{"value": Infinity}',
                   b'{"value": 1e999}', b'\xff', b'{"value": "\\ud800"}',
                   ("[" * 70 + "0" + "]" * 70).encode(), (RAW + SECRET).encode()]
        for raw in invalid:
            with self.subTest(raw=raw), patch("continuity.traceability_providers.azure_transport.build_opener", return_value=Opener(Response(raw))):
                try: AzureHttpTransport(profile(), SECRET).request(("wit", "workitems"), {})
                except AzureTransportError as error: self.assert_sanitized(error)
                else: self.fail("expected malformed JSON failure")
        response = Response(b"x" * 101)
        with patch("continuity.traceability_providers.azure_transport.build_opener", return_value=Opener(response)):
            with self.assertRaisesRegex(AzureTransportError, "response_limit"):
                AzureHttpTransport(replace(profile(), limits=AzureLimits(max_response_bytes=100))).request(("wit", "workitems"), {})
        self.assertEqual(response.read_sizes, [101])
        for headers in ({"Content-Encoding": "gzip"}, {"x-ms-continuationtoken": "x" * 2049}, {"x-ms-continuationtoken": "x\n"}):
            with patch("continuity.traceability_providers.azure_transport.build_opener", return_value=Opener(Response(headers=headers))):
                with self.assertRaises(AzureTransportError): AzureHttpTransport(profile()).request(("wit", "workitems"), {})

    def test_sentinel_payload_never_enters_provider_or_report(self):
        fixture = RestFixture()
        for item in fixture.items:
            item["fields"]["System.AssignedTo"] = SECRET
            item["fields"]["System.Description"] = RAW
        e = AzureDevOpsTraceabilityProvider(profile(), IDENTITIES, STAMP, "synthetic-snapshot", fixture).acquire()
        for value in (repr(e), traceability_to_json(derive(e))):
            self.assertNotIn(SECRET, value)
            self.assertNotIn(RAW, value)

    def test_loopback_redirect_never_forwards_credentials_or_cookies(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get("Authorization"), self.headers.get("Cookie")))
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:" + str(self.server.server_port) + "/stolen")
                self.send_header("Set-Cookie", SECRET)
                self.end_headers()
                self.wfile.write((RAW + SECRET).encode())
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            configured = replace(profile(), base_url="http://127.0.0.1:" + str(server.server_port), allow_loopback_http=True)
            with self.assertRaisesRegex(AzureTransportError, "redirect_blocked"):
                AzureHttpTransport(configured, SECRET).request(("wit", "workitems"), {})
            self.assertEqual(len(requests), 1)
            self.assertIsNone(requests[0][2])
            self.assertNotIn(SECRET, requests[0][0])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_loopback_mode_does_not_allow_remote_http_or_unverified_https(self):
        for url in ("http://192.0.2.10", "http://synthetic.invalid", "http://127.0.0.1@synthetic.invalid"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                replace(profile(), base_url=url, allow_loopback_http=True)
        self.assertEqual(replace(profile(), base_url="http://127.0.0.1:1234", allow_loopback_http=True).base_url, "http://127.0.0.1:1234")
        for secret in ("", "x\n", "é", "x" * 4097):
            with self.assertRaises(ValueError): AzureHttpTransport(profile(), secret)

    def test_real_http_fixture_provider_derivation_and_serialization(self):
        fixture = RestFixture()
        versions = []
        class Handler(BaseHTTPRequestHandler):
            def serve(self):
                parsed = urlsplit(self.path)
                endpoint = tuple(parsed.path.split("/_apis/", 1)[1].split("/"))
                query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                versions.append(query.pop("api-version"))
                body = None
                if self.command == "POST":
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                response = fixture.request(endpoint, query, body)
                raw = json.dumps(response.payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                if response.continuation: self.send_header("x-ms-continuationtoken", response.continuation)
                self.end_headers(); self.wfile.write(raw)
            do_GET = serve
            do_POST = serve
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            configured = replace(profile(), base_url="http://127.0.0.1:" + str(server.server_port),
                                 allow_loopback_http=True, limits=AzureLimits(page_size=1))
            provider = AzureDevOpsTraceabilityProvider(configured, IDENTITIES, STAMP, "synthetic-snapshot", AzureHttpTransport(configured, SECRET))
            encoded = traceability_to_json(derive(provider.acquire()))
            expected = traceability_to_json(derive(AzureDevOpsTraceabilityProvider(profile(), IDENTITIES, STAMP, "synthetic-snapshot", RestFixture()).acquire()))
            self.assertEqual(encoded, expected)
            self.assertEqual(set(versions), {"7.2"})
            self.assertNotIn(SECRET, encoded)
            self.assertNotIn("127.0.0.1", encoded)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__": unittest.main()
