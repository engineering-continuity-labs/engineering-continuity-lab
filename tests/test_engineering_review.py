"""Source-design boundary and exact-arithmetic regressions (AC506/509)."""
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from dataclasses import replace
import unittest

from continuity.domain.engineering_review import Window, Windows, distribution, elapsed_microseconds
from continuity.analysis.engineering_review import Lifecycle, State, Transition, analyze_population
from continuity.analysis.delivery_runs import Build, BuildResult, PRState, PullRequest, analyze_builds, analyze_prs
from continuity.reporting.engineering_review import compose, import_package, public
from continuity.reporting.portable import canonical


class EngineeringReviewTests(unittest.TestCase):
    def test_partial_extension_preserves_earlier_complete_inventory(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        windows = Windows.default(end)
        base = Lifecycle(('WORK_ITEM', 'azure', 'atlas', 'project', 'B'), 'earlier', windows.previous.start,
                         State.OPEN, windows.previous.start, windows.previous.end, True, ())
        later = replace(base, observation='later', history_end=end, history_complete=False)
        previous = analyze_population((base, later), windows.previous, enumeration_complete=True, created_start=True)
        self.assertEqual(previous.open_inventory, 1)
        self.assertEqual(previous.availability, 'OBSERVED')
        self.assertIsNone(analyze_population((base, later), windows.current,
                                            enumeration_complete=True, created_start=True).open_inventory)

    def test_pr_boundary_and_distinct_immutable_states(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        windows = Windows.default(end)
        ref = ('PR', 'azure', 'atlas', 'repo', 'boundary')
        boundary = PullRequest(ref, PRState.OPEN, end, end, None)
        self.assertEqual(analyze_prs((boundary,), windows.current, enumeration_complete=True).open_inventory, 0)
        ref = ('PR', 'azure', 'atlas', 'repo', 'changing')
        created = windows.previous.start + timedelta(days=1)
        previous = PullRequest(ref, PRState.OPEN, windows.previous.end, created, None, 'previous')
        merged = PullRequest(ref, PRState.MERGED, end, created, end - timedelta(days=1), 'current')
        observations = (previous, merged)
        self.assertEqual(analyze_prs(observations, windows.previous, enumeration_complete=True).open_inventory, 1)
        current = analyze_prs(observations, windows.current, enumeration_complete=True)
        self.assertEqual(current.merged, 1)
        self.assertEqual(current.open_inventory, 0)
        self.assertFalse(current.conflicts)
        unknown = replace(previous, state=PRState.UNKNOWN)
        old = analyze_prs((unknown, merged), windows.previous, enumeration_complete=True)
        self.assertIsNone(old.open_inventory)
        self.assertFalse(old.inventory_complete)
        self.assertEqual(old.inventory_unknown, 1)
        impossible = replace(merged, merged_at=windows.previous.end - timedelta(days=5))
        inconsistent = analyze_prs((previous, impossible), windows.previous, enumeration_complete=True)
        self.assertIsNone(inconsistent.merged)
        self.assertIsNone(inconsistent.open_inventory)

    def test_build_in_progress_observation_can_extend_to_terminal(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        windows = Windows.default(end)
        first = Build(('BUILD', 'azure', 'atlas', 'pipeline', 'run'), BuildResult.UNKNOWN,
                      False, end - timedelta(hours=2), None, 'in-progress')
        finished = replace(first, terminal=True, result=BuildResult.FAILURE,
                           finish_at=end - timedelta(hours=1), observation='finished')
        result = analyze_builds((first, finished), windows.current, enumeration_complete=True)
        self.assertFalse(result.conflicts)
        self.assertEqual(result.known_terminal, 1)
        self.assertEqual(result.unfinished, 0)
        self.assertEqual(result.failure_fraction, 1)

    def test_package_roundtrip_recomputes_and_rejects_forgery(self) -> None:
        windows = Windows.default(datetime(2026, 10, 1, tzinfo=timezone.utc))
        package = compose(assessment_id='review', system='atlas', windows=windows)
        self.assertEqual(import_package(canonical(package)), package)
        package['assessment']['findings'] = [{'rule_id': 'ER09'}]
        with self.assertRaisesRegex(ValueError, '^invalid engineering package$'):
            import_package(canonical(package))
        with self.assertRaises(ValueError):
            import_package('{"assessment":{},"assessment":{},"evidence":{}}')

    def test_package_build_oracle_and_normalized_order(self) -> None:
        windows = Windows.default(datetime(2026, 10, 1, tzinfo=timezone.utc))
        finish = windows.current.end - timedelta(days=1)
        builds = [public(Build(('BUILD', 'azure', 'atlas', 'pipeline', str(i)), result, True,
                               finish - timedelta(minutes=(i + 1) * 2), finish)) for i, result in enumerate(
                                   (BuildResult.SUCCESS, BuildResult.SUCCESS, BuildResult.FAILURE, BuildResult.PARTIAL_SUCCESS))]
        source = {'schema_version': 'delivery-evidence-1', 'system': 'atlas', 'alias': 'synthetic',
                  'retrieved_at': '2026-10-01T00:00:00Z', 'policy_fingerprint': 'policy',
                  'selection_fingerprint': 'selection', 'capability': 'SUPPORTED', 'status': 'COMPLETE',
                  'created_start': False, 'work_items': [], 'pull_requests': [], 'builds': builds}
        source['populations'] = {name: {'capability': 'SUPPORTED', 'status': 'COMPLETE',
                                      'provider': 'azure', 'instance': 'atlas',
                                      'scope': {'work_items': 'project', 'pull_requests': 'repo', 'builds': 'pipeline'}[name],
                                      'repository': 'repo'}
                                 for name in ('work_items', 'pull_requests', 'builds')}
        source['categories'] = {name: {'capability': 'UNSUPPORTED', 'values': [], 'fingerprint': 'none'}
                                for name in ('priority', 'severity')}
        source.update(mappings=[], mapping_complete=False, mapping_revision='unavailable')
        source.update(selected_types=['item'], publication_approved=True)
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=source)
        self.assertEqual(import_package(canonical(package)), package)
        self.assertEqual([f['rule_id'] for f in package['assessment']['findings']], ['ER09'])
        source['builds'] = list(reversed(builds))
        self.assertEqual(compose(assessment_id='review', system='atlas', windows=windows, delivery=source), package)
        source['secret'] = 'private'
        with self.assertRaises(ValueError):
            compose(assessment_id='review', system='atlas', windows=windows, delivery=source)

    def test_unknown_state_future_creation_and_distinct_observations(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        window = Window(end - timedelta(days=30), end)
        base = Lifecycle(('WORK_ITEM', 'azure', 'atlas', 'project', 'B'), 'first', window.start,
                         State.OPEN, window.start, end, True, ())
        unknown = replace(base, transitions=(Transition('unknown', 1, window.start + timedelta(days=1),
                                                        State.OPEN, State.UNKNOWN),))
        metric = analyze_population((unknown,), window, enumeration_complete=True, created_start=True)
        self.assertIsNone(metric.open_inventory)
        self.assertIsNone(metric.completed)
        self.assertEqual(metric.availability, 'PARTIAL')
        with self.assertRaises(ValueError):
            replace(base, created_at=end + timedelta(days=1))
        observations = analyze_population((base, replace(base, observation='second')), window,
                                          enumeration_complete=True, created_start=True)
        self.assertFalse(observations.conflicts)
        self.assertEqual(observations.open_inventory, 1)

    def test_build_oracle_distinguishes_partial_success(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        window = Window(end - timedelta(days=30), end)
        finish = end - timedelta(days=1)
        results = (BuildResult.SUCCESS, BuildResult.SUCCESS, BuildResult.FAILURE, BuildResult.PARTIAL_SUCCESS)
        builds = tuple(Build(('BUILD', 'azure', 'atlas', 'pipeline', str(i)), result, True,
                             finish - timedelta(minutes=(i + 1) * 2), finish) for i, result in enumerate(results))
        metric = analyze_builds(builds, window, enumeration_complete=True)
        self.assertEqual(metric.success_fraction, Fraction(1, 2))
        self.assertEqual(metric.failure_fraction, Fraction(1, 4))
        self.assertEqual(metric.durations.median, 300000000)
        self.assertEqual(metric, analyze_builds(tuple(reversed(builds)) + (builds[0],), window,
                                              enumeration_complete=True))
        unknown = Build(('BUILD', 'azure', 'atlas', 'pipeline', 'unknown'), BuildResult.UNKNOWN,
                        True, None, finish)
        self.assertEqual(analyze_builds(builds + (unknown,), window,
                                       enumeration_complete=True).known_terminal, 4)
        empty = analyze_builds((), window, enumeration_complete=True)
        self.assertIsNone(empty.success_fraction)

    def test_pr_inventory_requires_exact_boundary_and_actual_merge(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        window = Window(end - timedelta(days=30), end)
        created = end - timedelta(days=31)
        opened = PullRequest(('PR', 'azure', 'atlas', 'repo', 'open'), PRState.OPEN, end, created, None)
        merged = PullRequest(('PR', 'azure', 'atlas', 'repo', 'merged'), PRState.MERGED, end,
                             created, end - timedelta(days=1))
        abandoned = PullRequest(('PR', 'azure', 'atlas', 'repo', 'abandoned'), PRState.ABANDONED,
                                end, created, None)
        metric = analyze_prs((opened, merged, abandoned), window, enumeration_complete=True)
        self.assertEqual(metric.merged, 1)
        self.assertEqual(metric.open_inventory, 1)
        self.assertEqual(metric.lead.median, 30 * 86400000000)
        self.assertEqual(metric.open_ages[0][1], 31 * 86400000000)
        later = PullRequest(opened.reference, PRState.OPEN, end + timedelta(days=1), created, None)
        self.assertIsNone(analyze_prs((later,), window, enumeration_complete=True).open_inventory)
        conflict = analyze_prs((opened, later), window, enumeration_complete=True)
        self.assertEqual(conflict.conflicts, (opened.reference,))
        self.assertIsNone(conflict.open_inventory)
        with self.assertRaises(ValueError):
            PullRequest(abandoned.reference, PRState.ABANDONED, end, created, end - timedelta(days=1))

    def test_atlas_bug_source_oracle(self) -> None:
        def date(month: int, day: int) -> datetime:
            return datetime(2026, month, day, tzinfo=timezone.utc)
        window = Window(date(9, 1), date(10, 1))
        rows = ((date(9, 1), ((5, State.COMPLETE),)),
                (date(9, 3), ((10, State.COMPLETE), (15, State.OPEN), (20, State.COMPLETE))),
                (date(9, 21), ()), (date(8, 17), ()),
                (date(9, 10), ((12, State.REMOVED),)),
                (date(8, 28), ((22, State.REMOVED),)))
        records = []
        for index, (created, events) in enumerate(rows):
            state = State.OPEN
            transitions = []
            for sequence, (day, target) in enumerate(events):
                transitions.append(Transition(f'e{index}-{sequence}', sequence, date(9, day), state, target))
                state = target
            records.append(Lifecycle(('WORK_ITEM', 'azure', 'atlas', 'project', f'B{index + 1}'),
                                     'observation', created, State.OPEN, created,
                                     window.end, True, tuple(transitions)))
        result = analyze_population(tuple(records), window, enumeration_complete=True, created_start=True)
        self.assertEqual((result.opened, result.completed, result.reopened, result.open_inventory, result.aged),
                         (4, 2, 1, 2, 1))
        self.assertEqual(sum(len(r.completions) for r in result.results), 3)
        self.assertEqual(result.durations.median, Fraction(9 * 86400000000, 2))
        self.assertIsNone(result.durations.p75)
        self.assertEqual(result, analyze_population(tuple(reversed(records)) + (records[0],), window,
                                                   enumeration_complete=True, created_start=True))

    def test_history_unknown_and_empty_are_distinct(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        window = Window(end - timedelta(days=30), end)
        empty = analyze_population((), window, enumeration_complete=True, created_start=True)
        self.assertEqual(empty.completed, 0)
        self.assertEqual(empty.reopened, 0)
        self.assertIsNone(empty.durations.median)
        failed = analyze_population((), window, enumeration_complete=False, created_start=True)
        self.assertIsNone(failed.completed)
        created = window.start
        partial = Lifecycle(('WORK_ITEM', 'azure', 'atlas', 'project', 'B'), 'observation', created,
                            State.OPEN, created, end, False,
                            (Transition('completion', 1, created + timedelta(days=2), State.OPEN, State.COMPLETE),))
        observed = analyze_population((partial,), window, enumeration_complete=True, created_start=True)
        self.assertEqual(observed.completed, 1)
        self.assertIsNone(observed.reopened)
        self.assertIsNone(observed.open_inventory)
        self.assertIsNone(observed.durations.median)
        self.assertEqual(observed.availability, 'PARTIAL')

    def test_complete_utc_days_and_half_open_boundary(self) -> None:
        now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        windows = Windows.default(now)
        self.assertEqual(windows.current.start, datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertEqual(windows.previous.start, datetime(2026, 8, 2, tzinfo=timezone.utc))
        self.assertTrue(windows.current.contains(windows.current.start))
        self.assertFalse(windows.current.contains(windows.current.end))
        self.assertEqual(Windows.default(now.astimezone(timezone(timedelta(hours=3)))), windows)

    def test_reject_invalid_windows_and_naive_instants(self) -> None:
        end = datetime(2026, 10, 1, tzinfo=timezone.utc)
        current = Window(end - timedelta(days=30), end)
        for previous in (Window(end - timedelta(days=61), current.start),
                         Window(end - timedelta(days=61), end - timedelta(days=31)),
                         Window(end - timedelta(days=59), end - timedelta(days=29))):
            with self.assertRaises(ValueError):
                Windows(current, previous, end)
        with self.assertRaises(ValueError):
            Windows.default(datetime(2026, 10, 1))
        with self.assertRaises(ValueError):
            Window(end, end)
        with self.assertRaises(ValueError):
            Windows(current, Window(end - timedelta(days=60), current.start), end - timedelta(seconds=1))

    def test_accepted_oracles_and_minimum_samples(self) -> None:
        normal = distribution((2, 4, 6, 8))
        self.assertEqual(normal.median, 5)
        self.assertEqual(normal.p75, 6)
        self.assertIsNone(normal.p90)
        self.assertEqual(distribution((4, 5)).median, Fraction(9, 2))
        self.assertIsNone(distribution((1, 2, 3)).p75)
        self.assertIsNone(distribution(tuple(range(9))).p90)
        self.assertEqual(distribution(tuple(range(1, 11))).p90, 9)
        self.assertIsNone(distribution(()).median)
        self.assertEqual(distribution((8, 2, 6, 4)), normal)
        for sample in ((True,), (-1,), (1.5,)):
            with self.assertRaises(ValueError):
                distribution(sample)  # type: ignore[arg-type]

    def test_elapsed_retains_microseconds_and_rejects_inversion(self) -> None:
        start = datetime(2026, 9, 1, tzinfo=timezone.utc)
        self.assertEqual(elapsed_microseconds(start, start + timedelta(days=4, microseconds=1)),
                         345600000001)
        with self.assertRaises(ValueError):
            elapsed_microseconds(start, start - timedelta(microseconds=1))
