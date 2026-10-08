"""Immutable, acquisition-private Azure deployment and identity configuration."""
from dataclasses import dataclass, field
from enum import StrEnum
import ipaddress
import math
import re
from urllib.parse import quote, urlencode, urlsplit
from uuid import UUID

from continuity.domain.traceability import safe_token


class AzureDevOpsDeployment(StrEnum):
    SERVER = "SERVER"
    SERVICES = "SERVICES"


class AzureApiProfile(StrEnum):
    SERVER_CURRENT = "SERVER_CURRENT"
    SERVER_2022_1 = "SERVER_2022_1"
    SERVER_2022 = "SERVER_2022"
    SERVICES = "SERVICES"


_VERSIONS = {AzureApiProfile.SERVER_CURRENT: "7.2", AzureApiProfile.SERVER_2022_1: "7.1",
             AzureApiProfile.SERVER_2022: "7.0", AzureApiProfile.SERVICES: "7.2"}
_PRIVATE = re.compile(r"(?:https?://|gh[pousr]_|github_pat_|glpat-|sk-[A-Za-z0-9_-]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|authorization|bearer|password|cookie|secret|token|pat[_=: ])", re.I)


def public_alias(value: str) -> None:
    safe_token(value)
    if _PRIVATE.search(value):
        raise ValueError("invalid approved alias")


def guid(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        raise ValueError("invalid Azure scope identity")
    try:
        result = str(UUID(value))
    except ValueError:
        raise ValueError("invalid Azure scope identity") from None
    if result != value.lower():
        raise ValueError("invalid Azure scope identity")
    return result


def native_id(value: object) -> int:
    if type(value) is not int or not 0 < value <= 2**31 - 1:
        raise ValueError("invalid Azure artifact identity")
    return value


@dataclass(frozen=True)
class AzureLimits:
    timeout: float = 15.0
    max_response_bytes: int = 2_000_000
    page_size: int = 100
    max_pages: int = 100
    max_items: int = 10_000
    work_item_batch: int = 200
    max_relations: int = 1_000
    max_requests: int = 2_000

    def __post_init__(self) -> None:
        if (isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float))
                or not math.isfinite(self.timeout) or not 0 < self.timeout <= 300):
            raise ValueError("invalid Azure limits")
        for value, maximum in ((self.max_response_bytes, 20_000_000), (self.page_size, 200),
                               (self.max_pages, 1_000), (self.max_items, 100_000),
                               (self.work_item_batch, 200), (self.max_relations, 10_000), (self.max_requests, 100_000)):
            if type(value) is not int or not 0 < value <= maximum:
                raise ValueError("invalid Azure limits")


@dataclass(frozen=True, repr=False)
class AzureIdentityMap:
    """Caller-approved aliases; private reverse identities never enter evidence."""
    fingerprint: str
    work_items: tuple[tuple[int, str], ...]
    pull_requests: tuple[tuple[int, str], ...]

    def __post_init__(self) -> None:
        public_alias(self.fingerprint)
        for entries in (self.work_items, self.pull_requests):
            if not isinstance(entries, tuple) or any(not isinstance(e, tuple) or len(e) != 2 for e in entries):
                raise ValueError("invalid approved identity map")
            keys: set[int] = set()
            aliases: set[str] = set()
            for identifier, alias in entries:
                native_id(identifier)
                public_alias(alias)
                if identifier in keys or alias in aliases:
                    raise ValueError("duplicate approved identity map")
                keys.add(identifier)
                aliases.add(alias)

    def alias(self, identifier: int, *, work_item: bool) -> str:
        entries = self.work_items if work_item else self.pull_requests
        for key, alias in entries:
            if key == identifier:
                return alias
        raise ValueError("unapproved Azure artifact identity")


@dataclass(frozen=True, repr=False)
class AzureDevOpsProfile:
    deployment: AzureDevOpsDeployment
    api_profile: AzureApiProfile
    base_url: str
    collection: str
    project: str
    repository: str
    instance_alias: str
    project_alias: str
    repository_alias: str
    revision: str
    api_version: str | None = None
    include_changes: bool = True
    include_artifact_relations: bool = True
    allow_loopback_http: bool = False
    limits: AzureLimits = field(default_factory=AzureLimits)

    def __post_init__(self) -> None:
        if not isinstance(self.deployment, AzureDevOpsDeployment) or not isinstance(self.api_profile, AzureApiProfile):
            raise ValueError("invalid Azure deployment profile")
        services = self.api_profile == AzureApiProfile.SERVICES
        if services != (self.deployment == AzureDevOpsDeployment.SERVICES):
            raise ValueError("incompatible Azure deployment profile")
        version = _VERSIONS[self.api_profile] if self.api_version is None else self.api_version
        allowed = tuple(v for v in ("7.0", "7.1", "7.2") if v <= _VERSIONS[self.api_profile])
        if version not in allowed:
            raise ValueError("incompatible Azure API version")
        object.__setattr__(self, "api_version", version)
        for flag in (self.include_changes, self.include_artifact_relations, self.allow_loopback_http):
            if type(flag) is not bool:
                raise ValueError("invalid Azure operation configuration")
        if not isinstance(self.limits, AzureLimits):
            raise ValueError("invalid Azure limits")
        object.__setattr__(self, "project", guid(self.project))
        object.__setattr__(self, "repository", guid(self.repository))
        for alias in (self.instance_alias, self.project_alias, self.repository_alias):
            public_alias(alias)
        if not re.fullmatch(r"[0-9a-f]{40}", self.revision):
            raise ValueError("invalid Azure revision")
        if (not self.collection or len(self.collection) > 256
                or any(c in self.collection for c in "/\\%?#@:")
                or self.collection in (".", "..") or any(ord(c) < 32 or ord(c) == 127 for c in self.collection)):
            raise ValueError("invalid Azure collection")
        try:
            u = urlsplit(self.base_url)
            port = u.port
        except ValueError:
            raise ValueError("invalid Azure base URL") from None
        if (not u.hostname or u.username is not None or u.password is not None or u.query or u.fragment
                or any(ord(c) <= 32 or ord(c) == 127 for c in self.base_url)
                or "\\" in self.base_url or "%" in self.base_url
                or any(p in (".", "..") for p in u.path.split("/"))
                or "//" in u.path):
            raise ValueError("invalid Azure base URL")
        if u.scheme != "https":
            try:
                loopback = ipaddress.ip_address(u.hostname).is_loopback
            except ValueError:
                loopback = u.hostname == "localhost"
            if u.scheme != "http" or not self.allow_loopback_http or not loopback:
                raise ValueError("Azure HTTPS required")
        if services and u.scheme == "https" and (u.hostname != "dev.azure.com" or u.path not in ("", "/") or port not in (None, 443)):
            raise ValueError("invalid Azure Services origin")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    def url(self, endpoint: tuple[str, ...], query: dict[str, str] | None = None) -> str:
        """Encode each path segment once; version cannot be overridden by a query."""
        if any(not p or p in (".", "..") or "/" in p or "\\" in p for p in endpoint):
            raise ValueError("invalid Azure endpoint")
        params = dict(query or {})
        if "api-version" in params:
            raise ValueError("Azure API version belongs to profile")
        params["api-version"] = str(self.api_version)
        segments = (self.collection, self.project, "_apis") + endpoint
        return self.base_url + "/" + "/".join(quote(s, safe="") for s in segments) + "?" + urlencode(sorted(params.items()))
