"""Project-owned SYNTHETIC Azure-shaped REST data; never offline BASE input."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import re

from continuity.traceability_providers.azure_devops import (
    AzureApiProfile, AzureDevOpsDeployment, AzureDevOpsProfile, AzureIdentityMap,
)
from continuity.traceability_providers.azure_transport import AzureResponse, AzureTransportError

PROJECT = "11111111-1111-4111-8111-111111111111"
REPOSITORY = "22222222-2222-4222-8222-222222222222"
FOREIGN = "33333333-3333-4333-8333-333333333333"
STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
ISO = "2026-01-01T00:00:00.000000Z"
IDENTITIES = AzureIdentityMap("synthetic-approved-v1", ((1001, "wi-1001"), (1002, "wi-1002"), (1003, "wi-1003")),
                             tuple((i, f"pr-{i}") for i in (51, 52, 53, 54)))


def profile(kind=AzureApiProfile.SERVER_CURRENT, **kwargs):
    services = kind == AzureApiProfile.SERVICES
    return AzureDevOpsProfile(AzureDevOpsDeployment.SERVICES if services else AzureDevOpsDeployment.SERVER,
        kind, "https://dev.azure.com" if services else "https://synthetic.invalid/tfs", "synthetic-collection",
        PROJECT, REPOSITORY, "ecl-synthetic", "demo-project", "demo-system", "d" * 40, **kwargs)


def artifact(family, target, *, project=PROJECT, repository=REPOSITORY, encoded=False):
    suffix = f"{project}/{repository}/{target}"
    return "vstfs:///Git/" + family + "/" + (suffix.replace("/", "%2f") if encoded else suffix)


class RestFixture:
    def __init__(self):
        self.calls = []
        self.fail = {}
        self.mutate = {}
        self.no_token = False
        self.repeat_token = False
        self.prs = [{"pullRequestId": i, "status": "completed", "closedDate": "2025-12-31T23:59:59.1234567Z",
                     "repository": {"id": REPOSITORY, "project": {"id": PROJECT}},
                     "workItemRefs": [{"id": str(w)} for w in {51: [1001, 1002], 52: [], 53: [1002], 54: [1001]}[i]],
                     "title": "SYNTHETIC private title PR-999 WI-1003", "createdBy": {"displayName": "PERSON_SENTINEL"}}
                    for i in (51, 52, 53, 54)]
        self.commits = [{"commitId": c * 40, "comment": "SYNTHETIC MESSAGE_SENTINEL WI-1003"} for c in "abcd"]
        self.members = {51: [self.commits[0], self.commits[1]], 52: [self.commits[2]], 53: [self.commits[3]], 54: []}
        self.items = [{"id": i, "fields": {"System.Id": i, "System.WorkItemType": t, "System.State": s,
                     "System.Title": "TITLE_SENTINEL", "System.AssignedTo": {"displayName": "PERSON_SENTINEL"},
                     "System.Description": "DESCRIPTION_SENTINEL"},
                     "relations": [{"rel": "ArtifactLink", "url": artifact("Commit", "c" * 40, encoded=True)}] if i == 1002 else []}
                     for i, t, s in ((1001, "User Story", "Active"), (1002, "Bug", "Closed"), (1003, "Requirement", "New"))]
        self.changes = {c * 40: [{"item": {"path": "/" + path, "gitObjectType": "blob"}}] for c, path in zip("abcd",
                        ("src/payments/retry.py", "tests/payments/test_retry.py", "src/catalog/timeout.py", "src/payments/timeout.py"))}

    def request(self, endpoint, query, body=None):
        self.calls.append((endpoint, deepcopy(query), deepcopy(body)))
        key = (endpoint, int(query.get("$skip", query.get("skip", "0"))))
        failure = self.fail.get(key, self.fail.get(endpoint))
        if failure:
            raise AzureTransportError("unsupported" if failure == "unsupported" else "request_failed", unsupported=failure == "unsupported")
        token = None
        if endpoint == ("wit", "wiql"):
            cursor = int(re.search(r"\[System.Id\] > ([0-9]+)", body["query"])[1])
            ids = sorted({r["id"] for r in self.items if isinstance(r.get("id"), int) and r["id"] > cursor})
            payload = {"queryType": "flat", "asOf": ISO, "workItems": [{"id": i} for i in ids[:int(query["$top"])]]}
        elif endpoint == ("wit", "workitems"):
            ids = set(map(int, query["ids"].split(",")))
            payload = {"value": [i for i in self.items if i.get("id") in ids]}
        elif endpoint[-1] == "pullrequests":
            start, size = int(query["$skip"]), int(query["$top"])
            payload = {"value": self.prs[start:start + size]}
        elif len(endpoint) == 5 and endpoint[3] == "pullrequests":
            payload = next((p for p in self.prs if p["pullRequestId"] == int(endpoint[4])), {})
        elif len(endpoint) == 6 and endpoint[3] == "pullrequests" and endpoint[-1] == "workitems":
            payload = {"value": [{"id": "1001"}] if endpoint[4] == "51" else []}
        elif len(endpoint) == 6 and endpoint[3] == "pullrequests":
            start, size = int(query.get("continuationToken", "0")), int(query["$top"])
            records = self.members[int(endpoint[4])]
            payload = {"value": records[start:start + size]}
            if start + size <= len(records) and not self.no_token:
                token = "0" if self.repeat_token else str(start + size)
        elif endpoint[-1] == "commits":
            start, size = int(query["$skip"]), int(query["$top"])
            payload = {"value": self.commits[start:start + size]}
        elif endpoint[-1] == "changes":
            start, size = int(query["skip"]), int(query["top"])
            payload = {"changes": self.changes[endpoint[4]][start:start + size]}
        else:
            raise AssertionError("unexpected synthetic endpoint")
        mutation = self.mutate.get(key, self.mutate.get(endpoint))
        if mutation:
            payload = mutation(deepcopy(payload))
        return AzureResponse(deepcopy(payload), token)
