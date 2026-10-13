"""Read-only Azure projection; native configuration/DTOs never form public evidence."""
from argparse import Namespace
from dataclasses import dataclass
from datetime import datetime, timezone
import getpass
from hashlib import sha256
from pathlib import Path
import sys
import tomllib
from typing import Any
import warnings

from continuity.private_input import read_private
from continuity.azure_connection import Connection, _aliases, _table, _text, load_connection
from continuity.analysis.engineering_review import Lifecycle, State, Transition
from continuity.analysis.delivery_runs import Build, BuildResult, PullRequest, PRState
from continuity.domain.engineering_review import Window, Windows
from continuity.reporting.engineering_review import compose, import_package, public
from continuity.reporting.portable import canonical, loads
from continuity.traceability_providers.azure_dto import array, obj, timestamp, text
from continuity.traceability_providers.azure_profile import AzureIdentityMap, native_id, public_alias, guid
from continuity.traceability_providers.azure_transport import AzureHttpTransport, AzureTransport, AzureTransportError


@dataclass(frozen=True, repr=False)
class ReviewConnection:
    connection: Connection
    system: str
    assessment: str
    windows: Windows
    project_name: str
    delivery_types: dict[str, str]
    defect_types: dict[str, str]
    states: dict[str, State]
    created_start: bool
    definitions: tuple[int, ...]
    builds: tuple[tuple[int, str], ...]


def load_review(path: Path) -> ReviewConnection:
    contents = read_private(path, 1_048_576)
    raw = _table(tomllib.loads(contents.decode('utf-8')), {'review', 'selection', 'states', 'builds'})
    r = _table(raw['review'], {'connection_file', 'system', 'assessment', 'previous_start', 'current_start',
                             'current_end', 'assessment_as_of'})
    c = load_connection(path.parent / _text(r, 'connection_file'))
    for k in ('system', 'assessment'):
        public_alias(_text(r, k))
    windows = Windows(Window(timestamp(r['current_start']), timestamp(r['current_end'])),
                      Window(timestamp(r['previous_start']), timestamp(r['current_start'])),
                      timestamp(r['assessment_as_of']))
    if c.collected_at < windows.assessment_as_of:
        raise ValueError('invalid observation cutoff')
    s = _table(raw['selection'], {'project_name', 'delivery_types', 'defect_types', 'created_start', 'build_definitions'})
    if type(s['created_start']) is not bool:
        raise ValueError('invalid start policy')
    types = []
    for key in ('delivery_types', 'defect_types'):
        values = _table(s[key], set(), set(s[key]) if isinstance(s[key], dict) else set())
        if not 1 <= len(values) <= 100:
            raise ValueError('invalid type selection')
        for k, v in values.items():
            if not isinstance(k, str) or not k or len(k) > 100 or any(ord(x) < 32 for x in k):
                raise ValueError('invalid private type')
            public_alias(v)
        if len(set(values.values())) != len(values):
            raise ValueError('invalid type aliases')
        types.append(values)
    if set(types[0]) & set(types[1]) or set(types[0].values()) & set(types[1].values()):
        raise ValueError('overlapping populations')
    states = _table(raw['states'], set(), set(raw['states']) if isinstance(raw['states'], dict) else set())
    if not 1 <= len(states) <= 100 or any(not k or len(k) > 100 for k in states):
        raise ValueError('invalid state policy')
    policy = {k: State(v) for k, v in states.items()}
    definitions = s['build_definitions']
    if not isinstance(definitions, list) or not 1 <= len(definitions) <= 100:
        raise ValueError('invalid build selection')
    definitions = tuple(sorted({native_id(v) for v in definitions}))
    builds = _aliases(raw['builds'])
    # Reuse strict unique native/public alias validation, without changing connection schema.
    AzureIdentityMap(c.identities.fingerprint, builds, ())
    return ReviewConnection(c, r['system'], r['assessment'], windows, _text(s, 'project_name'), types[0], types[1], policy,
                            s['created_start'], definitions, builds)


def observation_time() -> datetime:
    return datetime.now(timezone.utc)


class Acquisition:
    """Bounded ephemeral projection. Live non-atomic enumeration is never certified complete."""
    def __init__(self, config: ReviewConnection, transport: AzureTransport, *, observed_at: datetime | None = None):
        self.config = config
        self.observed_at = observed_at or observation_time()
        if self.observed_at.utcoffset() is None or self.observed_at < config.connection.collected_at:
            raise ValueError('observation precedes cutoff')
        self.transport = transport
        self.requests = 0
        self.events = 0
        self.profile = config.connection.profile
        if getattr(transport, 'profile', self.profile) != self.profile:
            raise ValueError('mismatched transport')

    def __repr__(self) -> str:
        return '<Azure engineering acquisition>'

    def request(self, endpoint: tuple[str, ...], query: dict[str, str],
                body: dict[str, str] | None = None) -> Any:
        if self.requests >= self.profile.limits.max_requests:
            raise AzureTransportError('response_limit')
        self.requests += 1
        return self.transport.request(endpoint, query, body)

    def scan(self, endpoint: tuple[str, ...], query: dict[str, str], *, continuation: bool = False) -> tuple[list[Any], str]:
        records: list[Any] = []
        token = None
        seen: set[str] = set()
        try:
            for page in range(self.profile.limits.max_pages):
                q = {**query, '$top': str(self.profile.limits.page_size)}
                if continuation:
                    if token is not None:
                        q['continuationToken'] = token
                else:
                    q['$skip'] = str(page * self.profile.limits.page_size)
                response = self.request(endpoint, q)
                values = array(obj(response.payload)['value'])
                if len(values) > self.profile.limits.page_size:
                    return records, 'PARTIAL'
                remaining = min(self.profile.limits.max_items, 10000) - len(records)
                records.extend(values[:remaining])
                if len(values) > remaining:
                    return records, 'PARTIAL'
                if continuation:
                    token = response.continuation
                    if token is None:
                        return records, 'PARTIAL'
                    if (not isinstance(token, str) or not token or len(token) > 2048
                            or any(ord(c) < 32 or ord(c) == 127 for c in token) or token in seen):
                        return records, 'PARTIAL'
                    seen.add(token)
                elif len(values) < self.profile.limits.page_size:
                    return records, 'COMPLETE'
            return records, 'PARTIAL'
        except AzureTransportError as error:
            return records, 'PARTIAL' if records else ('UNSUPPORTED' if error.unsupported else 'FAILED')
        except (ValueError, TypeError, KeyError, OverflowError):
            return records, 'PARTIAL' if records else 'FAILED'

    def ids(self) -> tuple[list[int], str]:
        ids: set[int] = set()
        cursor = 0
        cutoff = public(self.config.connection.collected_at)
        try:
            for _ in range(self.profile.limits.max_pages):
                response = self.request(('wit', 'wiql'), {'$top': str(self.profile.limits.page_size), 'timePrecision': 'true'},
                                        {'query': 'SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project '
                                         f"AND [System.Id] > {cursor} ORDER BY [System.Id] ASC ASOF '{cutoff}'"})
                d = obj(response.payload)
                if d.get('queryType') != 'flat' or timestamp(d.get('asOf')) != self.config.connection.collected_at:
                    raise ValueError('invalid selection')
                values = array(d['workItems'])
                if len(values) > self.profile.limits.page_size:
                    break
                valid = []
                malformed = False
                for value in values:
                    try:
                        identifier = native_id(obj(value)['id'])
                        if identifier <= cursor:
                            raise ValueError('nonprogress')
                        valid.append(identifier)
                    except (ValueError, TypeError, KeyError):
                        malformed = True
                ids.update(valid)
                if len(ids) > min(self.profile.limits.max_items, 10000):
                    ids = set(sorted(ids)[:min(self.profile.limits.max_items, 10000)])
                    break
                if malformed or not valid or len(values) < self.profile.limits.page_size:
                    break
                cursor = max(valid)
            return sorted(ids), 'PARTIAL'
        except AzureTransportError as error:
            return sorted(ids), 'PARTIAL' if ids else ('UNSUPPORTED' if error.unsupported else 'FAILED')
        except (ValueError, TypeError, KeyError, OverflowError):
            return sorted(ids), 'PARTIAL' if ids else 'FAILED'

    def reference(self, kind: str, identifier: int) -> tuple[str, str, str, str, str]:
        aliases = (dict(self.config.builds) if kind == 'BUILD' else
                   dict(self.config.connection.identities.work_items if kind == 'WORK_ITEM'
                        else self.config.connection.identities.pull_requests))
        return kind, 'azure-devops', self.profile.instance_alias, self.profile.project_alias, aliases[identifier]

    def unique(self, records: list[Any], key: str) -> list[dict[str, Any]]:
        groups: dict[int, dict[str, dict[str, Any]]] = {}
        for raw in records:
            try:
                d = obj(raw)
                identifier = native_id(d[key])
                groups.setdefault(identifier, {})[canonical(d)] = d
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        return [next(iter(values.values())) for _, values in sorted(groups.items()) if len(values) == 1]

    def lifecycle(self, identifier: int, raw: list[Any]) -> Lifecycle | None:
        revisions = self.unique(raw, 'rev')
        if not revisions:
            return None
        fields = [obj(r['fields']) for r in revisions]
        cutoff = self.config.connection.collected_at
        # Reject conflicts/gaps before truncating future observations.
        if len(revisions) != len({native_id(obj(v)['rev']) for v in raw}):
            raise ValueError('conflicting revision')
        if any(native_id(r['id']) != identifier or native_id(r['rev']) != i + 1 for i, r in enumerate(revisions)):
            raise ValueError('incomplete revision prefix')
        times = [timestamp(f['System.ChangedDate']) for f in fields]
        created = timestamp(fields[0]['System.CreatedDate'])
        if times != sorted(times) or times[0] != created or any(timestamp(f['System.CreatedDate']) != created for f in fields):
            raise ValueError('invalid revision times')
        if any(f.get('System.TeamProject') != self.config.project_name for f in fields):
            raise ValueError('wrong WI project')
        kinds = {text(f['System.WorkItemType']) for f in fields}
        if len(kinds) != 1:
            raise ValueError('type mutation')
        kind = next(iter(kinds))
        selected = {**self.config.delivery_types, **self.config.defect_types}
        if kind not in selected:
            return None
        ref = self.reference('WORK_ITEM', identifier)
        kept = [(f, t, r) for f, t, r in zip(fields, times, revisions) if t <= cutoff]
        if not kept:
            return None
        states = [self.config.states.get(text(f['System.State']), State.UNKNOWN) for f, _, _ in kept]
        if State.UNKNOWN in states:
            raise ValueError('unknown state')
        events = []
        for i, (_, stamp, revision) in enumerate(kept[1:], 1):
            if states[i] != states[i - 1]:
                if self.events >= 40000:
                    raise ValueError('event limit')
                event = sha256(canonical([ref, revision['rev']]).encode()).hexdigest()
                events.append(Transition(event, revision['rev'], stamp, states[i - 1], states[i]))
                self.events += 1
        return Lifecycle(ref, 'azure-revisions', created, states[0], created, cutoff, True, tuple(events),
                         None, None, selected[kind], 'SUPPORTED', None)

    def pr(self, d: dict[str, Any]) -> PullRequest:
        from continuity.traceability_providers.azure_dto import pull_request
        pull_request(d, project=self.profile.project, repository=self.profile.repository, read_refs=False)
        identifier = native_id(d['pullRequestId'])
        cutoff = self.config.connection.collected_at
        created = timestamp(d['creationDate'])
        state = {'active': PRState.OPEN, 'completed': PRState.MERGED, 'abandoned': PRState.ABANDONED}[d['status']]
        # A newer change cannot be represented as a historical state snapshot.
        closed = timestamp(d['closedDate']) if d.get('closedDate') is not None else None
        if created > cutoff or closed is not None and closed > cutoff:
            raise ValueError('future PR')
        if state == PRState.MERGED and (d.get('mergeStatus') != 'succeeded' or closed is None):
            raise ValueError('unconfirmed merge')
        return PullRequest(self.reference('PR', identifier), state, self.observed_at, created,
                           closed if state == PRState.MERGED else None, 'azure-pr-list')

    def build(self, d: dict[str, Any]) -> Build:
        if (guid(obj(d['project'])['id']) != self.profile.project
                or guid(obj(d['repository'])['id']) != self.profile.repository
                or obj(d['repository']).get('type') != 'TfsGit'
                or native_id(obj(d['definition'])['id']) not in self.config.definitions
                or d.get('deleted', False) is not False):
            raise ValueError('wrong build scope')
        identifier = native_id(d['id'])
        status = d['status']
        if status not in ('completed', 'inProgress', 'notStarted', 'cancelling', 'postponed'):
            raise ValueError('unknown build status')
        terminal = status == 'completed'
        result = {'succeeded': BuildResult.SUCCESS, 'failed': BuildResult.FAILURE,
                  'partiallySucceeded': BuildResult.PARTIAL_SUCCESS, 'canceled': BuildResult.CANCELED}.get(text(d['result']) if d.get('result') is not None else '', BuildResult.UNKNOWN)
        start = timestamp(d['startTime']) if d.get('startTime') is not None else None
        finish = timestamp(d['finishTime']) if d.get('finishTime') is not None else None
        if not terminal and (finish is not None or result != BuildResult.UNKNOWN):
            raise ValueError('contradictory build')
        if any(t is not None and t > self.config.connection.collected_at for t in (start, finish)):
            raise ValueError('future build')
        return Build(self.reference('BUILD', identifier), result, terminal, start, finish, 'azure-build-list')

    def acquire(self) -> tuple[dict[str, Any], dict[str, Any]]:
        ids, wi_status = self.ids()
        delivery_items: list[Any] = []
        defect_items: list[Any] = []
        history_statuses = []
        for identifier in ids:
            records, status = self.scan(('wit', 'workitems', str(identifier), 'revisions'), {})
            history_statuses.append(status)
            try:
                # Short final page proves revision pagination ended; live source remains partial.
                if status != 'COMPLETE' or not records:
                    continue
                item = self.lifecycle(identifier, records)
                if item is not None:
                    target = delivery_items if item.type_alias in self.config.delivery_types.values() else defect_items
                    target.append(public(item))
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        if ids and all(s in ('FAILED', 'UNSUPPORTED') for s in history_statuses):
            wi_status = 'UNSUPPORTED' if all(s == 'UNSUPPORTED' for s in history_statuses) else 'FAILED'
        repo = ('git', 'repositories', self.profile.repository, 'pullrequests')
        raw_prs, pr_status = self.scan(repo, {'searchCriteria.status': 'all'})
        raw_builds, build_status = self.scan(('build', 'builds'), {'definitions': ','.join(map(str, self.config.definitions)),
                                                            'repositoryId': self.profile.repository, 'repositoryType': 'TfsGit',
                                                            'deletedFilter': 'exclude'}, continuation=True)
        prs = []
        builds = []
        for raw in self.unique(raw_prs, 'pullRequestId'):
            try:
                prs.append(public(self.pr(raw)))
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        for raw in self.unique(raw_builds, 'id'):
            try:
                builds.append(public(self.build(raw)))
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        return (self.collection('delivery', delivery_items, prs, builds, wi_status, pr_status, build_status),
                self.collection('quality', defect_items, [], [], wi_status, 'UNSUPPORTED', 'UNSUPPORTED'))

    def collection(self, role: str, items: list[Any], prs: list[Any], builds: list[Any],
                   wi_status: str, pr_status: str, build_status: str) -> dict[str, Any]:
        cfg = self.config
        types = cfg.delivery_types if role == 'delivery' else cfg.defect_types
        selected = {'types': types, 'definitions': cfg.definitions, 'project': self.profile.project,
                    'repository': self.profile.repository, 'project_name': cfg.project_name, 'identity_fingerprint': cfg.connection.identities.fingerprint,
                    'build_aliases': cfg.builds, 'role': role, 'population': 'nondeleted-bounded-live-partial'}
        policy = {'states': public(cfg.states), 'created_start': True if role == 'quality' else cfg.created_start, 'adapter': 'azure-engineering-1'}
        def coverage(status: str) -> dict[str, Any]:
            return {'capability': 'UNSUPPORTED' if status == 'UNSUPPORTED' else 'SUPPORTED',
                    'status': 'FAILED' if status in ('FAILED', 'UNSUPPORTED') else 'PARTIAL',
                    'provider': 'azure-devops', 'instance': self.profile.instance_alias,
                    'scope': self.profile.project_alias, 'repository': self.profile.repository_alias}
        active = [wi_status, pr_status, build_status] if role == 'delivery' else [wi_status]
        failed = all(s in ('FAILED', 'UNSUPPORTED') for s in active)
        return {'schema_version': f'{role}-evidence-1', 'system': cfg.system,
                'alias': f'azure-{role}-bounded-live-partial', 'retrieved_at': public(self.observed_at),
                'policy_fingerprint': sha256(canonical(policy).encode()).hexdigest(),
                'selection_fingerprint': sha256(canonical(selected).encode()).hexdigest(),
                'capability': 'SUPPORTED', 'status': 'FAILED' if failed else 'PARTIAL',
                'created_start': True if role == 'quality' else cfg.created_start,
                'work_items': items, 'pull_requests': prs, 'builds': builds,
                'populations': {'work_items': coverage(wi_status), 'pull_requests': coverage(pr_status), 'builds': coverage(build_status)},
                'categories': {k: {'capability': 'UNSUPPORTED', 'values': [], 'fingerprint': 'not-collected'} for k in ('priority', 'severity')},
                'mappings': [], 'mapping_complete': False, 'mapping_revision': cfg.connection.profile.revision,
                'selected_types': sorted(types.values()), 'publication_approved': True}


def run(args: Namespace) -> int:
    try:
        if not args.approve_publication:
            raise ValueError()
        cfg = load_review(args.config)
        report = None
        if args.report:
            content = read_private(args.report, 32 * 1024 * 1024)
            report = loads(content)
            compose(assessment_id=cfg.assessment, system=cfg.system, windows=cfg.windows, ecl_report=report)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError):
        print('continuity: invalid or unapproved engineering review configuration', file=sys.stderr)
        return 2
    pat = None
    try:
        if not args.anonymous:
            if not sys.stdin.isatty():
                raise ValueError()
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                pat = getpass.getpass('Azure read-only PAT (hidden): ')
            if not pat:
                raise ValueError()
        transport = AzureHttpTransport(cfg.connection.profile, pat)
    except (ValueError, EOFError, KeyboardInterrupt, getpass.GetPassWarning, OSError):
        print('continuity: Azure authentication input unavailable', file=sys.stderr)
        return 2
    finally:
        pat = None
    try:
        delivery, quality = Acquisition(cfg, transport).acquire()
        package = compose(assessment_id=cfg.assessment, system=cfg.system, windows=cfg.windows,
                          delivery=delivery, quality=quality, ecl_report=report)
        output = canonical(import_package(canonical(package)))
        if args.format == 'html':
            from continuity.reporting.engineering_html import render
            output = render(package)
        print(output)
        return 4 if delivery['status'] == quality['status'] == 'FAILED' else 3
    except KeyboardInterrupt:
        print('continuity: engineering review interrupted', file=sys.stderr)
        return 2
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError):
        print('continuity: engineering review processing failed', file=sys.stderr)
        return 2
