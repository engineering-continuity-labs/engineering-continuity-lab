"""Bounded stdlib transport. No response body or native URL in failures."""
import base64
from dataclasses import dataclass
import json
import math
import re
import ssl
from http.client import HTTPException
from typing import Any, Never, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from continuity.traceability_providers.azure_profile import AzureDevOpsProfile


class AzureTransportError(Exception):
    def __init__(self, category: str, *, unsupported: bool = False) -> None:
        self.category = category if category in ("request_failed", "unsupported", "invalid_response", "response_limit", "redirect_blocked") else "request_failed"
        self.unsupported = unsupported
        super().__init__(self.category)


@dataclass(frozen=True, repr=False)
class AzureResponse:
    payload: object
    continuation: str | None = None


class AzureTransport(Protocol):
    def request(self, endpoint: tuple[str, ...], query: dict[str, str],
                body: dict[str, str] | None = None) -> AzureResponse: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid JSON")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("invalid JSON")


def _depth(value: object, depth: int = 0) -> None:
    if depth > 64:
        raise ValueError("invalid JSON")
    if isinstance(value, dict):
        for key, child in value.items():
            if any(0xD800 <= ord(c) <= 0xDFFF for c in key):
                raise ValueError("invalid JSON")
            _depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, depth + 1)
    elif isinstance(value, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("invalid JSON")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("invalid JSON")


class AzureHttpTransport:
    __slots__ = ("profile", "_pat")

    def __init__(self, profile: AzureDevOpsProfile, pat: str | None = None) -> None:
        self.profile = profile
        self._pat = pat
        if self._pat is not None and (not isinstance(self._pat, str) or not self._pat
                                    or len(self._pat) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in self._pat)):
            raise ValueError("invalid runtime Azure credential")

    def __reduce__(self) -> Never:
        raise TypeError("Azure transport is runtime-only")

    def request(self, endpoint: tuple[str, ...], query: dict[str, str],
                body: dict[str, str] | None = None) -> AzureResponse:
        repo = ("git", "repositories", self.profile.repository)
        valid = (endpoint in (("wit", "wiql"), ("wit", "workitems"), repo + ("pullrequests",), repo + ("commits",))
                 or (endpoint[:3] == repo and len(endpoint) == 6 and endpoint[3] == "pullrequests"
                     and re.fullmatch(r"[1-9][0-9]{0,9}", endpoint[4]) is not None and endpoint[5] in ("commits", "workitems"))
                 or (endpoint[:3] == repo and len(endpoint) == 5 and endpoint[3] == "pullrequests"
                     and re.fullmatch(r"[1-9][0-9]{0,9}", endpoint[4]) is not None)
                 or (endpoint[:3] == repo and len(endpoint) == 6 and endpoint[3] == "commits"
                     and re.fullmatch(r"[0-9a-f]{40}", endpoint[4]) is not None and endpoint[5] == "changes"))
        if not valid or (body is not None) != (endpoint == ("wit", "wiql")):
            raise AzureTransportError("request_failed")
        failure: AzureTransportError | None = None
        result: AzureResponse | None = None
        try:
            headers = {"Accept": "application/json"}
            if self._pat is not None:
                headers["Authorization"] = "Basic " + base64.b64encode((":" + self._pat).encode("ascii")).decode("ascii")
            data = None if body is None else json.dumps(body, ensure_ascii=True, allow_nan=False).encode("utf-8")
            if data is not None:
                headers["Content-Type"] = "application/json"
            req = Request(self.profile.url(endpoint, query), data=data, headers=headers,
                          method="GET" if data is None else "POST")
            opener = build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
            with opener.open(req, timeout=self.profile.limits.timeout) as response:
                if response.status != 200 or response.headers.get("Content-Encoding", "identity") != "identity":
                    raise AzureTransportError("invalid_response")
                raw = response.read(self.profile.limits.max_response_bytes + 1)
                if len(raw) > self.profile.limits.max_response_bytes:
                    raise AzureTransportError("response_limit")
                payload: object = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
                _depth(payload)
                token = response.headers.get("x-ms-continuationtoken")
                if token is not None and (not token or len(token) > 2048 or any(ord(c) < 32 or ord(c) == 127 for c in token)):
                    raise AzureTransportError("invalid_response")
                result = AzureResponse(payload, token)
        except HTTPError as error:
            code = error.code
            error.close()
            failure = AzureTransportError("redirect_blocked" if 300 <= code < 400 else
                                          "unsupported" if code in (405, 501) else "request_failed",
                                          unsupported=code in (405, 501))
        except AzureTransportError as error:
            failure = AzureTransportError(error.category, unsupported=error.unsupported)
        except (URLError, OSError, HTTPException, ValueError, TypeError, RecursionError, OverflowError):
            failure = AzureTransportError("invalid_response")
        # Raise outside the handler so the raw exception is not retained as __context__.
        if failure is not None:
            raise failure from None
        if result is None:
            raise AzureTransportError("request_failed")
        return result
