"""Explicit SYNTHETIC lifecycle source oracle, never real acquisition."""
from datetime import datetime, timedelta, timezone
from typing import Any

from continuity.analysis.delivery_runs import Build, BuildResult, PullRequest, PRState
from continuity.analysis.engineering_review import Lifecycle, State, Transition
from continuity.domain.engineering_review import Windows
from continuity.reporting.engineering_review import public


def sources() -> tuple[Windows, dict[str, Any], dict[str, Any]]:
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    windows = Windows.default(end)
    def envelope(name: str) -> dict[str, Any]:
        return {'schema_version': name + '-evidence-1', 'system': 'atlas', 'alias': 'synthetic-' + name,
                'retrieved_at': public(end), 'policy_fingerprint': name + '-policy-1', 'selection_fingerprint': name + '-selection-1',
                'publication_approved': True, 'capability': 'SUPPORTED', 'status': 'COMPLETE', 'created_start': True,
                'selected_types': ['item'], 'work_items': [], 'pull_requests': [], 'builds': [],
                'mappings': [], 'mapping_complete': False, 'mapping_revision': 'unavailable',
                'populations': {population: {'capability': 'SUPPORTED' if name == 'delivery' or population == 'work_items' else 'UNSUPPORTED',
                                             'status': 'COMPLETE', 'provider': 'synthetic', 'instance': 'atlas',
                                             'scope': {'work_items': 'project', 'pull_requests': 'repo', 'builds': 'pipeline'}[population],
                                             'repository': 'demo-system'} for population in ('work_items', 'pull_requests', 'builds')},
                'categories': {category: {'capability': 'SUPPORTED' if name == 'quality' else 'UNSUPPORTED',
                                         'values': ['P1', 'P2'] if category == 'priority' and name == 'quality' else
                                         ['S1', 'S2'] if name == 'quality' else [], 'fingerprint': category + '-policy-1'}
                               for category in ('priority', 'severity')}}
    delivery, quality = envelope('delivery'), envelope('quality')
    for period, window, durations in (('previous', windows.previous, (2, 4, 6, 8)),
                                      ('current', windows.current, (4, 8, 12, 16))):
        for index, days in enumerate(durations):
            completed = window.end - timedelta(days=index + 1)
            created = completed - timedelta(days=days)
            identity = f'{period}-{index}'
            record = Lifecycle(('WORK_ITEM', 'synthetic', 'atlas', 'project', identity), 'observation', created,
                               State.OPEN, created, end, True,
                               (Transition(identity + '-complete', 1, completed, State.OPEN, State.COMPLETE),))
            delivery['work_items'].append(public(record))
            delivery['pull_requests'].append(public(PullRequest(('PR', 'synthetic', 'atlas', 'repo', identity),
                                                               PRState.MERGED, end, created, completed)))
    created = end - timedelta(days=31)
    delivery['work_items'].append(public(Lifecycle(('WORK_ITEM', 'synthetic', 'atlas', 'project', 'open'),
                                                   'observation', created, State.OPEN, created, end, True, ())))
    delivery['pull_requests'].append(public(PullRequest(('PR', 'synthetic', 'atlas', 'repo', 'open'), PRState.OPEN,
                                                       end, created, None)))
    finish = end - timedelta(days=1)
    for index, result in enumerate((BuildResult.SUCCESS, BuildResult.SUCCESS, BuildResult.FAILURE, BuildResult.PARTIAL_SUCCESS)):
        delivery['builds'].append(public(Build(('BUILD', 'synthetic', 'atlas', 'pipeline', str(index)), result, True,
                                              finish - timedelta(minutes=(index + 1) * 2), finish)))
    rows = ((9, 1, ((5, State.COMPLETE),)), (9, 3, ((10, State.COMPLETE), (15, State.OPEN), (20, State.COMPLETE))),
            (9, 21, ()), (8, 17, ()), (9, 10, ((12, State.REMOVED),)), (8, 28, ((22, State.REMOVED),)))
    for index, (month, day, events) in enumerate(rows):
        created = datetime(2026, month, day, tzinfo=timezone.utc)
        state = State.OPEN
        transitions = []
        for sequence, (event_day, target) in enumerate(events):
            transitions.append(Transition(f'B{index + 1}-{sequence}', sequence,
                                           datetime(2026, 9, event_day, tzinfo=timezone.utc), state, target))
            state = target
        quality['work_items'].append(public(Lifecycle(('WORK_ITEM', 'synthetic', 'atlas', 'project', f'B{index + 1}'),
                                                      'observation', created, State.OPEN, created, end, True, tuple(transitions),
                                                      'P1' if index % 2 else 'P2', 'S1' if index % 2 else 'S2',
                                                      category_as_of=end)))
    return windows, delivery, quality
