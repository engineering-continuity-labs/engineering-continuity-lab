# Azure DevOps traceability provider

## Architecture decision (before implementation)

Profile → bounded HTTP → strict REST DTO parsing → normalization → existing immutable TraceabilityEvidenceCollection → existing derive → report v3. No domain, derivation, scoring, browser or UI changes.

Native project/repository GUIDs are required in this first increment. This avoids guessing identity from names or acquiring name-resolution metadata. Server base paths (such as /tfs) and the configured collection are preserved; Services uses its configured organization as collection. Public scope aliases are separate. An immutable approved numeric-ID→alias map owns WI/PR equality and an explicit public mapping fingerprint; unknown/unapproved IDs are quarantined, not copied or silently hashed. No reverse map enters provenance.

A caller supplies an exact commit revision, public snapshot alias and collection instant. Independent commits use that revision's ancestry. WIQL enumerates project IDs with ordered keyset pages and ASOF; field batches use the same asOf. PRs use provider completed state and Closed maxTime. Azure queries are not an atomic cross-service transaction: boundary records this selected policy, not a live consistency guarantee. Artifact targets outside the independently observed populations remain positive associations subject to existing offline boundary checks, never extend denominators.

DTO parsing projects only allowlisted values. WI fields are ID/type/state with relations only when enabled; title is always off. Explicit ArtifactLink values accept only Git/Commit or Git/PullRequestId, GUID scope and full SHA-1/positive PR ID. Either literal suffix separators or uniformly %2F-encoded separators are accepted once; mixed/double encoding, extra/query/credential data fail. Non-Git relations are ignored, unknown Git artifact families are rejected with incomplete evidence.

Transport exposes a relative endpoint request interface bound to one profile. Only implemented GET reads and POST wit/wiql read-query are allowed. No raw DTO response/error is exposed through provider results. PAT lives only in transport runtime memory; repr/pickle exclude/reject it. No redirects (including same-origin), environment proxies or cookie jar. HTTPS uses the default verified SSL context; HTTP requires explicit loopback synthetic-test mode. Response bytes, JSON nesting, pages, items, relation count, token size, batches and timeout are bounded.

Lookup ownership: outbound PR→commit and commit→path status follows its own endpoint; inverse commit memberships require full PR population and all membership pages. WI→PR requires both full PR association scan and its WI relation scan; inverse PR→WI requires full WI population and relation scan plus that PR's references. Direct WI→commit outbound follows WI relations; inverse commit→WI requires the full WI scan. Independent population status is recorded separately. Disabled operation is UNSUPPORTED; 405/501 is UNSUPPORTED, ambiguous failures (including 404) are UNKNOWN/FAILED. Positive pages followed by failure are PARTIAL. A failed empty required lookup is FAILED.

## REST references

Implementation follows Microsoft read contracts: [PR list](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-requests/get-pull-requests?view=azure-devops-rest-7.1), [PR commits](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-commits/get-pull-request-commits?view=azure-devops-rest-7.1), [revision commits](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/commits/get-commits?view=azure-devops-rest-7.1), [changes](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/commits/get-changes?view=azure-devops-rest-7.1), [work-item list](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/list?view=azure-devops-rest-7.1), [WIQL](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/wiql/query-by-wiql?view=azure-devops-rest-7.1). Profile targets follow the user-requested deployment matrix and [Microsoft version guidance](https://learn.microsoft.com/en-us/rest/api/azure/devops/?view=azure-devops-rest-5.0). Synthetic tests do not establish live 7.2 availability.

## Deployment and operation matrix

| Profile | Deployment | Default REST version | Explicit compatible overrides |
| --- | --- | --- | --- |
| SERVER_CURRENT (primary) | Server current | 7.2 | 7.0, 7.1, 7.2 |
| SERVER_2022_1 | Server 2022.1 | 7.1 | 7.0, 7.1 |
| SERVER_2022 | Server 2022 | 7.0 | 7.0 |
| SERVICES | Services | 7.2 | 7.0, 7.1, 7.2 |

These are explicit target profiles, not live compatibility certifications. Preview/unknown versions and upgrades beyond a Server profile are rejected. No probing or silent downgrade occurs. Server: `https://synthetic.invalid/tfs/{collection}/{projectGUID}/_apis/...`; Services: `https://dev.azure.com/{organization}/{projectGUID}/_apis/...`. Collection/organization is mandatory, encoded as one segment, never assumed to be DefaultCollection. Repository routes use native GUID; names are deliberately unsupported until separately resolved to exact IDs. Transport origin, collection and native GUIDs are not provenance fields.

| Read operation | Population/link | Paging | Capability |
| --- | --- | --- | --- |
| GET git/repositories/{repo}/pullrequests, completed/Closed maxTime | Independently selected PR population | $skip/$top | Supported target; failure remains scoped |
| GET pullrequests/{id}; fallback GET pullrequests/{id}/workitems when workItemRefs absent | WI_PR | References bounded; fallback finite response | Explicit provider associations only |
| GET pullrequests/{id}/commits | PR_COMMIT | $top + x-ms-continuationtoken → continuationToken | Full page without token conservatively PARTIAL; never invent a next token |
| GET git/repositories/{repo}/commits at itemVersion commit revision | Independent commit ancestry | $skip/$top | Links never expand this denominator |
| POST wit/wiql, SELECT IDs, @project, ID keyset, ASOF | Independent project WI population, including unlinked WIs | Ordered ID keyset + $top | Read-query POST; no writes |
| GET wit/workitems, fields ID/type/state, asOf, optional Relations | WI evidence; ArtifactLink Git/PullRequestId→WI_PR, Git/Commit→WI_COMMIT | Sorted unique IDs, batches ≤200 | Disabling relations makes WI_COMMIT UNSUPPORTED; complete PR reference scans can still support WI_PR |
| GET commits/{hash}/changes | COMMIT_PATH | **top/skip (without dollar signs)** | Optional; disabling changes is UNSUPPORTED |

All observed links have DIRECT_PROVIDER_LINK origin, including REST changes. Only existing derive generates PATH_COMPONENT/WI_COMPONENT/paths, gaps and coverage. A later exact local Git join retains its own DIRECT_SOURCE_LINK. PR snapshot paths are outside this increment. Unknown work-item process labels normalize to OTHER; standard User Story/Product Backlog Item, Requirement, Bug and Task labels are recognized. Azure .NET 7-digit fractional timestamps are accepted and reduced to domain microseconds; no original timestamp string is exported.

## Runtime usage

The library requires explicit config and publication approval. A separate [local connection CLI](azure-local-connection.md) loads non-secret TOML with private native scope and prompts for a runtime PAT; it never persists credentials. For a project-owned SYNTHETIC example:

```python
from datetime import datetime, timezone
from continuity.traceability_providers.azure_devops import (
    AzureDevOpsDeployment, AzureApiProfile, AzureDevOpsProfile,
    AzureIdentityMap, AzureHttpTransport, AzureDevOpsTraceabilityProvider,
)
from continuity.analysis.traceability import derive
from continuity.reporting.traceability import traceability_to_json

profile = AzureDevOpsProfile(
    deployment=AzureDevOpsDeployment.SERVER,
    api_profile=AzureApiProfile.SERVER_CURRENT,
    base_url="https://synthetic.invalid/tfs",
    collection="synthetic-collection",
    project="11111111-1111-4111-8111-111111111111",
    repository="22222222-2222-4222-8222-222222222222",
    instance_alias="ecl-synthetic", project_alias="demo-project",
    repository_alias="demo-system", revision="d" * 40,
)
identities = AzureIdentityMap(
    "synthetic-approved-v1", ((1001, "wi-one"),), ((51, "pr-one"),),
)
# Runtime PAT may be passed here from caller memory; never put it in config/files.
transport = AzureHttpTransport(profile)  # anonymous unless PAT supplied
provider = AzureDevOpsTraceabilityProvider(
    profile, identities, datetime.now(timezone.utc), "approved-snapshot", transport,
)
# Dedicated non-sensitive live environment only; synthetic.invalid is not a service.
# result = derive(provider.acquire())
# public_json = traceability_to_json(result)
```

The alias map must cover discovered PR/WI IDs; unknown IDs are quarantined with partial evidence. Fingerprint and aliases are caller-approved stable equality tokens, not computed from names. Changing the mapping requires a changed fingerprint. Approval of aliases, commit hashes and repository-relative paths remains an origin/publication responsibility that syntax cannot prove. Arbitrary native IDs are never used as fallback aliases.

## Auth, bounds and failure semantics

Optional PAT uses HTTP Basic with an empty username, exclusively in transport request memory. Caller restricts its permissions to code/work-item read access. The client cannot certify token permissions but exposes no write operation. Transport object is not a dataclass, has no secret-bearing repr, and rejects pickle; it has no storage/logging/credential-manager feature. Headers are allowlisted; no raw header collection, Set-Cookie, response body, URL or transport exception enters public evidence. HTTP failures contain fixed categories only, with raw exception context removed.

Default limits: timeout 15s; response 2,000,000 bytes; page size 100; 100 pages per enumeration; 10,000 records per enumeration; 200 WI per batch; 1,000 relations/references per item/PR; 2,000 requests per acquisition; continuation ≤2,048 chars; JSON depth ≤64. All limits are validated and immutable. Strict JSON rejects duplicate keys, malformed UTF-8, invalid Unicode, nonfinite numbers and excessive nesting. Offset endpoints require a short page to establish completion, so an exact final full page requires a bounded empty probe. Commit continuation follows a token even on a short page; repeated/malformed tokens or a full page without continuation cannot establish completeness. No retry hides a 429/service failure.

Valid pages/records remain after late failure, with partial lookups; first failed endpoints have FAILED lookup and UNKNOWN capability (405/501 UNSUPPORTED). Collection is FAILED only with no usable evidence; unrelated positives can keep it PARTIAL. Complete-empty supported lookups can establish MISSING only through unchanged offline derivation. Malformed/conflicting records have safe INVALID_OBSERVATION diagnostics; the existing conservative normalization may taint scoped or global lookups, never restore complete negatives. Invalid/non-Git URL-shaped ArtifactLinks do not become links.

## Synthetic validation and remaining gaps

`tests/azure_rest_fixture.py` owns all REST-shaped synthetic IDs/DTOs and never imports offline BASE. Tests cover every target profile, deterministic ordering, alias quarantine, direct artifacts, multi-WI/multi-commit membership, changes, pagination/continuation, 200-item batching, empty/zero populations, duplicates, malformed/cross-scope records, unavailable/partial evidence, transport sentinels, TLS, redirects and full loopback HTTP acquisition. BASE reproduces PR 3/4, commits 4/4, WI 2/3; src/payments 2/2, tests/payments 1/1 and src/catalog 1/1 through provider → derive → report v3, including browser round trip.

Live Server current/2022.1/2022 and Services REST behavior, proxy/certificate/auth deployment, continuation-header behavior and WIQL ASOF/field expansion compatibility remain MANUAL. Cross-service acquisition is not atomic; PR references/commit memberships lack historical ASOF support. Large histories can stop on finite bounds and require a separately designed selection flow. No OAuth/Entra, NTLM/Kerberos, name resolution, custom-process mappings, connection UI, arbitrary title export, PR_PATH acquisition, write operations or people scoring. Independent Code Reviewer approval and green applicable PR CI remain separate merge gates; AGENTS.md does not prescribe a human reviewer.

## Closure corrections

The independent post-merge review found four MAJOR defects in merged PR #20; their counterexamples and final re-review status are retained in [review history](validation/v0.3-azure-provider-review.md). Contradictory required WI labels now quarantine that native identity rather than selecting a representative; later duplicates cannot resurrect it, and independent PR references remain unresolved. On a malformed/nonprogress WIQL page, valid progressive IDs are enriched and the query stops PARTIAL without a guessed cursor. Both inline PR references and the dedicated fallback enforce max_relations; excess references cannot establish COMPLETE. Changed paths reject report-recognized credential markers before evidence construction, preserve existing stricter marker rejection and never copy the raw path into diagnostics. Ordinary paths, approved aliases and BASE behavior are preserved.

Fresh closure regressions are in `tests/test_azure_closure_review.py`; no domain/report/browser schema or derivation rules changed, and no new product capability was added. The historical developer preflight is preserved as history, independently of actual reviewer evidence. Live compatibility and publication-origin approval remain MANUAL.
