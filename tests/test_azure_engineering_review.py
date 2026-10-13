"""AC555–562 synthetic native REST oracles; no live deployment certification."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from io import StringIO
import json
import os
import subprocess
import sys
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from continuity.azure_engineering_review import Acquisition, load_review
from continuity.cli import main
from continuity.reporting.engineering_review import compose, import_package
from continuity.reporting.portable import canonical
from continuity.traceability_providers.azure_transport import AzureHttpTransport, AzureResponse, AzureTransportError
from test_azure_transport import Opener, Response
from urllib.parse import parse_qs, urlsplit

OBSERVED = datetime(2026, 1, 2, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
PROJECT = '11111111-1111-4111-8111-111111111111'
REPOSITORY = '22222222-2222-4222-8222-222222222222'


def revisions(identifier=1001, kind='Task'):
    values = []
    for rev, state, when in ((1, 'New', '2025-12-03T00:00:00Z'), (2, 'Active', '2025-12-04T00:00:00Z'),
                             (3, 'Closed', '2025-12-13T00:00:00Z')):
        values.append({'id': identifier, 'rev': rev, 'fields': {'System.WorkItemType': kind, 'System.State': state,
                       'System.TeamProject': 'Synthetic Project', 'System.CreatedDate': '2025-12-03T00:00:00Z',
                       'System.ChangedDate': when, 'System.Title': 'PRIVATE_TITLE_SENTINEL',
                       'System.Description': 'PRIVATE_DESCRIPTION_SENTINEL'}})
    return values


def pr(identifier=51, state='completed'):
    d = {'pullRequestId': identifier, 'status': state, 'mergeStatus': 'succeeded',
         'repository': {'id': REPOSITORY, 'project': {'id': PROJECT}},
         'creationDate': '2025-12-03T00:00:00Z', 'title': 'PRIVATE_TITLE_SENTINEL'}
    if state != 'active':
        d['closedDate'] = '2025-12-13T00:00:00Z'
    return d


def build(identifier=71, result='succeeded', status='completed'):
    d = {'id': identifier, 'project': {'id': PROJECT}, 'repository': {'id': REPOSITORY, 'type': 'TfsGit'},
         'definition': {'id': 7}, 'status': status, 'queueTime': '2025-12-03T00:00:00Z',
         'startTime': '2025-12-03T01:00:00Z', 'logs': {'url': 'PRIVATE_LOG_SENTINEL'}}
    if status == 'completed':
        d.update(result=result, finishTime='2025-12-03T01:10:00Z')
    return d


class Fixture:
    def __init__(self):
        self.ids = [1001, 1002]
        self.histories = {1001: revisions(), 1002: revisions(1002, 'Bug')}
        self.prs = [pr(), pr(52, 'active'), pr(53, 'abandoned')]
        self.builds = [build(71), build(72, 'failed'), build(73, 'partiallySucceeded'), build(74, 'canceled')]
        self.calls = []
        self.fail = {}
        self.token = None

    def request(self, endpoint, query, body=None):
        self.calls.append((endpoint, query, body))
        if endpoint in self.fail:
            raise AzureTransportError('request_failed', unsupported=self.fail[endpoint] == 'unsupported')
        if endpoint == ('wit', 'wiql'):
            cursor = int(re.search(r'Id\] > (\d+)', body['query']).group(1))
            values = [{'id': v} for v in self.ids if v > cursor][:int(query['$top'])]
            return AzureResponse({'queryType': 'flat', 'asOf': '2026-01-01T00:00:00Z', 'workItems': values})
        if endpoint[:2] == ('wit', 'workitems'):
            values = self.histories[int(endpoint[2])]
        elif endpoint[0] == 'build':
            values = self.builds
            return AzureResponse({'value': values[:int(query['$top'])]}, self.token)
        else:
            values = self.prs
        skip = int(query.get('$skip', 0))
        return AzureResponse({'value': values[skip:skip + int(query['$top'])]})


class AzureReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'PRIVATE_PATH_SENTINEL.toml'
        self.path.write_text((ROOT / 'examples/azure-engineering-review.toml').read_text())
        (self.path.parent / 'azure-connection.toml').write_text((ROOT / 'examples/azure-connection.toml').read_text())
        self.cfg = load_review(self.path)

    def acquire(self, fixture=None, cfg=None):
        return Acquisition(cfg or self.cfg, fixture or Fixture(), observed_at=OBSERVED).acquire()

    def package(self, fixture=None, cfg=None):
        cfg = cfg or self.cfg
        delivery, quality = self.acquire(fixture, cfg)
        return compose(assessment_id=cfg.assessment, system=cfg.system, windows=cfg.windows,
                       delivery=delivery, quality=quality)

    def invoke(self, fixture=None, options=('--anonymous', '--approve-publication'), tty=False):
        out, err = StringIO(), StringIO()
        with patch('continuity.azure_engineering_review.observation_time', return_value=OBSERVED), \
             patch('continuity.azure_engineering_review.AzureHttpTransport', return_value=fixture or Fixture()) as transport, \
             patch('continuity.azure_engineering_review.sys.stdin.isatty', return_value=tty), \
             patch('continuity.azure_engineering_review.getpass.getpass', return_value='PRIVATE_PAT_SENTINEL') as prompt, \
             redirect_stdout(out), redirect_stderr(err):
            code = main(['engineering-review', '--config', str(self.path), *options])
        return code, out.getvalue(), err.getvalue(), transport, prompt

    def test_native_projection_and_roundtrip(self):
        delivery, quality = self.acquire()
        self.assertEqual(len(delivery['work_items']), 1)
        self.assertEqual(len(quality['work_items']), 1)
        self.assertEqual(len(delivery['pull_requests']), 3)
        self.assertEqual(len(delivery['builds']), 4)
        self.assertEqual(delivery['work_items'][0]['transitions'][0]['next'], 'COMPLETE')
        # New→Active remains OPEN, so the true COMPLETE transition has native sequence 3.
        self.assertEqual(delivery['work_items'][0]['transitions'][0]['sequence'], 3)
        package = self.package()
        self.assertEqual(import_package(canonical(package)), package)
        self.assertIn('864000000000', canonical(package))  # exact 10-day creation-start duration
        self.assertIn('600000000', canonical(package))  # exact 10-minute build, not queue duration

    def test_honest_completeness_categories_and_mapping(self):
        delivery, quality = self.acquire()
        for source in (delivery, quality):
            self.assertEqual(source['status'], 'PARTIAL')
            self.assertFalse(source['mapping_complete'])
            self.assertEqual(source['categories']['severity']['capability'], 'UNSUPPORTED')
            self.assertEqual(source['mappings'], [])
        # Current retrieval only; preceding-window inventory cannot become OPEN.
        package = self.package()
        self.assertNotIn('ER06', canonical(package))
        for period in ('current', 'previous'):
            metrics = package['assessment']['dimension_results']['delivery'][period]['pull_requests']
            self.assertIsNone(metrics['open_inventory'])
            self.assertEqual(metrics['open_ages'], [])
        self.assertEqual(package['assessment']['dimension_results']['delivery']['current']['pull_requests']['lead']['count'], 1)

    def test_no_created_start_inference(self):
        cfg = replace(self.cfg, created_start=False)
        delivery, quality = self.acquire(cfg=cfg)
        self.assertFalse(delivery['created_start'])
        self.assertTrue(quality['created_start'])
        self.assertEqual(quality['policy_fingerprint'], self.acquire()[1]['policy_fingerprint'])
        package = self.package(cfg=cfg)
        self.assertEqual(package, import_package(canonical(package)))

    def test_revision_gaps_conflicts_unknown_scope_type_and_time(self):
        mutations = [lambda rows: rows.pop(1), lambda rows: rows.append({**deepcopy(rows[1]), 'fields': {}}),
                     lambda rows: rows[1]['fields'].update({'System.State': 'Unmapped'}),
                     lambda rows: rows[1]['fields'].update({'System.WorkItemType': 'Bug'}),
                     lambda rows: rows[1]['fields'].update({'System.TeamProject': 'Wrong Project'}),
                     lambda rows: rows[1].update(id=999),
                     lambda rows: rows[1]['fields'].update({'System.ChangedDate': '2025-12-02T00:00:00Z'}),
                     lambda rows: rows[0]['fields'].pop('System.CreatedDate')]
        for mutate in mutations:
            f = Fixture(); mutate(f.histories[1001])
            d, q = self.acquire(f)
            self.assertEqual(d['work_items'], [])
            self.assertEqual(len(q['work_items']), 1)
            self.assertEqual(d['status'], 'PARTIAL')

    def test_equal_duplicates_and_reordering_are_deterministic(self):
        a = self.package()
        f = Fixture()
        f.histories[1001] = list(reversed(f.histories[1001])) + [deepcopy(f.histories[1001][0])]
        f.prs = list(reversed(f.prs)) + [deepcopy(f.prs[0])]
        f.builds = list(reversed(f.builds)) + [deepcopy(f.builds[0])]
        self.assertEqual(a, self.package(f))

    def test_conflicting_pr_build_identity_quarantined(self):
        f = Fixture(); f.prs.append({**pr(), 'status': 'active'}); f.builds.append(build(71, 'failed'))
        d, _ = self.acquire(f)
        self.assertEqual(len(d['pull_requests']), 2)
        self.assertEqual(len(d['builds']), 3)
        self.assertNotIn('build-71', canonical(d['builds']))

    def test_unapproved_ids_and_wrong_scope_never_exported(self):
        f = Fixture(); f.prs.append(pr(999)); f.builds.append(build(999)); f.ids.append(999); f.histories[999] = revisions(999)
        f.prs[0]['repository']['project']['id'] = REPOSITORY
        f.builds[0]['repository']['id'] = PROJECT
        d, _ = self.acquire(f)
        self.assertEqual(len(d['pull_requests']), 2)
        self.assertEqual(len(d['builds']), 3)
        self.assertEqual(len(d['work_items']), 1)

    def test_future_terminal_events_are_not_backdated(self):
        f = Fixture(); f.prs[0]['closedDate'] = '2026-01-02T00:00:00Z'; f.builds[0]['finishTime'] = '2026-01-02T00:00:00Z'
        f.histories[1001][2]['fields']['System.ChangedDate'] = '2026-01-02T00:00:00Z'
        d, _ = self.acquire(f)
        self.assertEqual(d['work_items'][0]['transitions'], [])
        self.assertEqual(len(d['pull_requests']), 2)
        self.assertEqual(len(d['builds']), 3)

    def test_build_unknown_unfinished_and_missing_start_preserved(self):
        f = Fixture(); f.builds = [build(71, 'unknown'), build(72, status='inProgress'), build(73)]
        del f.builds[2]['startTime']
        d, _ = self.acquire(f)
        self.assertEqual(d['builds'][0]['result'], 'UNKNOWN')
        self.assertFalse(d['builds'][1]['terminal'])
        self.assertIsNone(d['builds'][2]['start_at'])
        self.package(f)

    def test_unconfirmed_merge_and_nonterminal_result_rejected(self):
        f = Fixture(); f.prs[0]['mergeStatus'] = 'conflicts'; f.builds[0]['status'] = 'inProgress'
        d, _ = self.acquire(f)
        self.assertEqual(len(d['pull_requests']), 2)
        self.assertEqual(len(d['builds']), 3)

    def test_budget_and_pagination_limits(self):
        for limits in (replace(self.cfg.connection.profile.limits, max_requests=1),
                       replace(self.cfg.connection.profile.limits, page_size=2, max_pages=1),
                       replace(self.cfg.connection.profile.limits, max_items=1)):
            cfg = replace(self.cfg, connection=replace(self.cfg.connection, profile=replace(self.cfg.connection.profile, limits=limits)))
            f = Fixture(); d, q = self.acquire(f, cfg)
            self.assertLessEqual(len(f.calls), limits.max_requests)
            self.assertLessEqual(len(d['work_items']), limits.max_items)
            if limits.max_pages == 1 or limits.max_requests == 1:
                self.assertEqual(d['work_items'], [])
            self.assertEqual(d['status'], 'FAILED' if limits.max_requests == 1 else 'PARTIAL')
            self.package(f, cfg)

    def test_repeat_build_continuation_stops_and_deduplicates(self):
        f = Fixture(); f.token = 'same-token'
        d, _ = self.acquire(f)
        self.assertEqual(len([c for c in f.calls if c[0] == ('build', 'builds')]), 2)
        self.assertEqual(len(d['builds']), 4)

    def test_failed_and_unsupported_populations(self):
        f = Fixture(); f.fail = {('wit', 'wiql'): 'failure', ('build', 'builds'): 'unsupported',
                                ('git', 'repositories', REPOSITORY, 'pullrequests'): 'failure'}
        code, out, err, _, _ = self.invoke(f)
        self.assertEqual((code, err), (4, ''))
        package = import_package(out)
        self.assertIn('UNSUPPORTED', canonical(package))
        self.assertNotIn('PRIVATE_', out)

    def test_json_html_privacy_and_runtime_pat(self):
        code, out, err, transport, prompt = self.invoke(options=('--approve-publication',), tty=True)
        self.assertEqual((code, err), (3, ''))
        prompt.assert_called_once_with('Azure read-only PAT (hidden): ')
        self.assertEqual(transport.call_args.args[1], 'PRIVATE_PAT_SENTINEL')
        package = import_package(out)
        code, html, err, _, _ = self.invoke(options=('--anonymous', '--approve-publication', '--format', 'html'))
        self.assertEqual((code, err), (3, ''))
        script = re.search(r'<script[^>]+type="application/json"[^>]*>(.*?)</script>', html, re.S).group(1)
        self.assertEqual(import_package(script), package)
        for sentinel in (PROJECT, REPOSITORY, 'synthetic.invalid', 'PRIVATE_', 'Synthetic Project'):
            self.assertNotIn(sentinel, out + html + err)
        self.assertNotIn('SYNTHETIC MANAGER EXAMPLE', html)
        self.assertNotIn('fetch(', html)

    def test_approval_auth_config_and_parser_fail_before_network(self):
        for options in (('--anonymous',), ('--approve-publication',), ('--anonymous', '--approve-publication', '--secret', 'PRIVATE_SECRET')):
            code, out, err, transport, prompt = self.invoke(options=options)
            self.assertEqual((code, out), (2, ''))
            transport.assert_not_called(); prompt.assert_not_called()
            self.assertNotIn('PRIVATE_', err)
        self.path.write_text(self.path.read_text().replace('created_start = true', 'created_start = "PRIVATE_SECRET"'))
        code, out, err, transport, _ = self.invoke()
        self.assertEqual((code, out), (2, '')); transport.assert_not_called()
        self.assertNotIn('PRIVATE_', err)

    def test_bad_optional_report_rejected_before_network(self):
        p = self.path.parent / 'PRIVATE_REPORT.json'; p.write_text('{"secret":"PRIVATE_SECRET"}')
        code, out, err, transport, _ = self.invoke(options=('--anonymous', '--approve-publication', '--report', str(p)))
        self.assertEqual((code, out), (2, '')); transport.assert_not_called()
        self.assertNotIn('PRIVATE_', err)

    def test_four_profile_versions_and_read_only_new_transport_routes(self):
        connection = self.path.parent / 'azure-connection.toml'
        original = connection.read_text()
        for kind, deployment, origin, version in (
            ('SERVER_CURRENT', 'SERVER', 'https://synthetic.invalid/tfs', '7.2'),
            ('SERVER_2022_1', 'SERVER', 'https://synthetic.invalid/tfs', '7.1'),
            ('SERVER_2022', 'SERVER', 'https://synthetic.invalid/tfs', '7.0'),
            ('SERVICES', 'SERVICES', 'https://dev.azure.com', '7.2')):
            connection.write_text(original.replace('SERVER_CURRENT', kind).replace('deployment = "SERVER"', f'deployment = "{deployment}"').replace('https://synthetic.invalid/tfs', origin))
            cfg = load_review(self.path)
            opener = Opener(Response())
            with patch('continuity.traceability_providers.azure_transport.build_opener', return_value=opener):
                transport = AzureHttpTransport(cfg.connection.profile)
                for route in (('build', 'builds'), ('wit', 'workitems', '1001', 'revisions')):
                    transport.request(route, {'$top': '10'})
                    request = opener.calls[-1][0]
                    self.assertEqual(request.get_method(), 'GET')
                    self.assertEqual(parse_qs(urlsplit(request.full_url).query)['api-version'], [version])
                    with self.assertRaises(AzureTransportError):
                        transport.request(route, {}, {'query': 'mutation'})
                for route in (('build', 'builds', '71', 'logs'), ('wit', 'workitems', '1001', 'updates'),
                              ('wit', 'workitems', '../secret', 'revisions'), ('build', 'definitions')):
                    with self.assertRaises(AzureTransportError):
                        transport.request(route, {})

    def test_valid_prefix_pages_required_for_history(self):
        cfg = replace(self.cfg, connection=replace(self.cfg.connection, profile=replace(self.cfg.connection.profile,
                      limits=replace(self.cfg.connection.profile.limits, page_size=2))))
        f = Fixture()
        d, q = self.acquire(f, cfg)
        self.assertEqual(len(d['work_items']), 1)
        self.assertEqual(len(q['work_items']), 1)
        class FailingPage(Fixture):
            def request(self, endpoint, query, body=None):
                if endpoint == ('wit', 'workitems', '1001', 'revisions') and query['$skip'] == '2':
                    raise AzureTransportError('request_failed')
                return super().request(endpoint, query, body)
        d, q = self.acquire(FailingPage(), cfg)
        self.assertEqual(d['work_items'], [])
        self.assertEqual(len(q['work_items']), 1)

    def test_nonprogress_selection_retains_valid_ids(self):
        class BrokenSelection(Fixture):
            def request(self, endpoint, query, body=None):
                if endpoint == ('wit', 'wiql'):
                    return AzureResponse({'queryType': 'flat', 'asOf': '2026-01-01T00:00:00Z',
                                          'workItems': [{'id': 0}, {'id': 1001}, {'id': 'secret'}]})
                return super().request(endpoint, query, body)
        d, _ = self.acquire(BrokenSelection())
        self.assertEqual(len(d['work_items']), 1)
        self.assertEqual(d['status'], 'PARTIAL')

    def test_transition_limit_quarantines_over_budget_item(self):
        a = Acquisition(self.cfg, Fixture(), observed_at=OBSERVED)
        a.events = 40000
        with self.assertRaises(ValueError):
            a.lifecycle(1001, revisions())

    def test_all_histories_failed_and_mixed_survivors(self):
        f = Fixture()
        f.fail = {('wit', 'workitems', '1001', 'revisions'): 'failure',
                  ('wit', 'workitems', '1002', 'revisions'): 'failure',
                  ('build', 'builds'): 'failure',
                  ('git', 'repositories', REPOSITORY, 'pullrequests'): 'failure'}
        code, out, err, _, _ = self.invoke(f)
        self.assertEqual((code, err), (4, ''))
        package = import_package(out)
        self.assertEqual(package['evidence']['delivery']['status'], 'FAILED')
        self.assertEqual(package['evidence']['quality']['status'], 'FAILED')
        del f.fail[('wit', 'workitems', '1002', 'revisions')]
        code, out, err, _, _ = self.invoke(f)
        self.assertEqual((code, err), (3, ''))
        self.assertEqual(len(import_package(out)['evidence']['quality']['work_items']), 1)
        f.ids = []; f.fail = {}
        code, out, err, _, _ = self.invoke(f)
        self.assertEqual((code, err), (3, ''))
        self.assertEqual(import_package(out)['evidence']['quality']['status'], 'PARTIAL')

    def test_nonregular_input_never_blocks_or_reflects_path(self):
        # Separate process timeout would fail if a future reader blocks on FIFO.
        for kind in ('review', 'connection', 'report'):
            with TemporaryDirectory() as tmp:
                base = Path(tmp)
                config = base / 'review.toml'
                config.write_text((ROOT / 'examples/azure-engineering-review.toml').read_text())
                connection = base / 'azure-connection.toml'
                connection.write_text((ROOT / 'examples/azure-connection.toml').read_text())
                fifo = {'review': config, 'connection': connection, 'report': base / 'PRIVATE_FIFO.json'}[kind]
                if fifo.exists(): fifo.unlink()
                os.mkfifo(fifo)
                args = [sys.executable, '-c', 'from continuity.cli import main; import sys; sys.exit(main())',
                        'engineering-review', '--config', str(config), '--anonymous', '--approve-publication']
                if kind == 'report': args.extend(['--report', str(fifo)])
                result = subprocess.run(args, capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertNotIn(str(base), result.stderr)
                self.assertNotIn('PRIVATE_FIFO', result.stderr)

    def test_optional_genuine_report_keeps_original_boundary(self):
        p = ROOT / 'examples/v0.4-traceability-v3.json'
        code, out, err, _, _ = self.invoke(options=('--anonymous', '--approve-publication', '--report', str(p)))
        self.assertEqual((code, err), (3, ''))
        package = import_package(out)
        self.assertEqual(package['evidence']['ecl_report'], json.loads(p.read_text()))
        self.assertEqual(package['assessment']['dimension_results']['legacy']['source_as_of'], '2026-01-01T00:00:00+00:00')

    def test_invalid_config_policies_are_rejected(self):
        original = self.path.read_text()
        changes = [('created_start = true', 'created_start = 1'),
                   ('build_definitions = [7]', 'build_definitions = [true]'),
                   ('Task = "delivery-task"', 'Task = "defect"'),
                   ('Bug = "defect"', 'Task = "defect"'),
                   ('Closed = "COMPLETE"', 'Closed = "bogus"'),
                   ('71 = "build-71"', '71 = "build-72"'),
                   ('2026-01-01T00:00:00Z', '2026-01-03T00:00:00Z')]
        for old, new in changes:
            self.path.write_text(original.replace(old, new))
            code, out, err, transport, _ = self.invoke()
            self.assertEqual((code, out), (2, ''))
            transport.assert_not_called()
        self.path.write_bytes(b'X' * 1_048_577)
        self.assertEqual(self.invoke()[0], 2)

    def test_config_and_acquisition_repr_private(self):
        self.assertNotIn(PROJECT, repr(self.cfg))
        self.assertNotIn('Synthetic Project', repr(self.cfg))
        self.assertNotIn(PROJECT, repr(Acquisition(self.cfg, Fixture(), observed_at=OBSERVED)))


if __name__ == '__main__':
    unittest.main()
