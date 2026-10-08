"""ECL-AC-357–360 local boundary tests; no external Azure service."""
from contextlib import redirect_stdout, redirect_stderr
import getpass
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import warnings

from azure_rest_fixture import RestFixture, PROJECT, REPOSITORY
from continuity.azure_connection import load_connection
from continuity.cli import main
from continuity.reporting.traceability import traceability_from_json

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/azure-connection.toml'


class AzureConnectionTests(unittest.TestCase):
    def invoke(self, contents=None, options=('--anonymous', '--approve-publication'), fixture=None, tty=False, prompt='SYNTHETIC_PAT'):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'PRIVATE_PATH_SENTINEL.toml'
            path.write_text(contents if contents is not None else EXAMPLE.read_text())
            out, err = StringIO(), StringIO()
            with patch('continuity.azure_connection.AzureHttpTransport', return_value=fixture or RestFixture()) as transport, \
                 patch('continuity.azure_connection.sys.stdin.isatty', return_value=tty), \
                 patch('continuity.azure_connection.getpass.getpass', return_value=prompt) as get, \
                 redirect_stdout(out), redirect_stderr(err):
                code = main(['azure-acquire', '--config', str(path), *options])
            return code, out.getvalue(), err.getvalue(), transport, get

    def test_all_profiles_and_config_projection(self):
        for kind, deployment, url, version in (
            ('SERVER_CURRENT', 'SERVER', 'https://synthetic.invalid/tfs', '7.2'),
            ('SERVER_2022_1', 'SERVER', 'https://synthetic.invalid/tfs', '7.1'),
            ('SERVER_2022', 'SERVER', 'https://synthetic.invalid/tfs', '7.0'),
            ('SERVICES', 'SERVICES', 'https://dev.azure.com', '7.2'),
        ):
            contents = EXAMPLE.read_text().replace('SERVER_CURRENT', kind).replace('deployment = "SERVER"', f'deployment = "{deployment}"').replace('https://synthetic.invalid/tfs', url)
            with TemporaryDirectory() as tmp:
                p = Path(tmp) / 'c.toml'; p.write_text(contents)
                c = load_connection(p)
            self.assertEqual(c.profile.api_version, version)
            self.assertEqual(c.profile.project, PROJECT)
            self.assertEqual(c.profile.repository, REPOSITORY)
            self.assertEqual(c.identities.alias(1001, work_item=True), 'wi-1001')
            self.assertEqual(c.component_depth, 2)
            self.assertEqual(c.collected_at.isoformat(), '2026-01-01T00:00:00+00:00')
            self.assertNotIn(PROJECT, repr(c))
            self.assertEqual(self.invoke(contents)[0], 0)

    def test_complete_roundtrip_and_no_private_fields(self):
        code, out, err, transport, get = self.invoke()
        self.assertEqual((code, err), (0, ''))
        report = traceability_from_json(out)
        self.assertEqual(report.evidence.status.value, 'COMPLETE')
        self.assertEqual(next(m for m in report.metrics if m.dimension == 'merged_pr_intent').numerator, 3)
        transport.assert_called_once(); get.assert_not_called()
        for sentinel in (PROJECT, REPOSITORY, 'synthetic.invalid', 'PRIVATE_PATH_SENTINEL', 'SYNTHETIC_PAT', 'TITLE_SENTINEL'):
            self.assertNotIn(sentinel, out + err)

    def test_partial_and_failed_exit_codes_preserve_reports(self):
        for failed, expected in ((False, 3), (True, 4)):
            f = RestFixture()
            if failed:
                f.fail = {('wit', 'wiql'): 'failure', ('git', 'repositories', REPOSITORY, 'pullrequests'): 'failure',
                          ('git', 'repositories', REPOSITORY, 'commits'): 'failure'}
            else:
                f.fail = {('git', 'repositories', REPOSITORY, 'commits', 'a' * 40, 'changes'): 'failure'}
            code, out, err, _, _ = self.invoke(fixture=f)
            self.assertEqual(code, expected)
            self.assertEqual(traceability_from_json(out).evidence.status.value, 'FAILED' if failed else 'PARTIAL')
            self.assertEqual(err, '')

    def test_publication_and_noninteractive_auth_fail_before_network(self):
        for options in (('--anonymous',), ('--approve-publication',)):
            code, out, err, transport, get = self.invoke(options=options)
            self.assertEqual((code, out), (2, ''))
            transport.assert_not_called(); get.assert_not_called()
            self.assertNotIn('PRIVATE_PATH_SENTINEL', err)

    def test_hidden_pat_passed_only_to_runtime_transport(self):
        code, out, err, transport, get = self.invoke(options=('--approve-publication',), tty=True)
        self.assertEqual(code, 0)
        get.assert_called_once_with('Azure read-only PAT (hidden): ')
        self.assertEqual(transport.call_args.args[1], 'SYNTHETIC_PAT')
        self.assertNotIn('SYNTHETIC_PAT', out + err)

    def test_bad_config_never_prompts_or_acquires(self):
        original = EXAMPLE.read_text()
        mutations = (
            original + '\npat = "PRIVATE_SECRET_SENTINEL"\n',
            original.replace('[connection]', '[connection]\npat = "PRIVATE_SECRET_SENTINEL"'),
            original.replace('[connection]', '[connection]\nallow_loopback_http = true'),
            original.replace('[connection]', '[connection]\nunknown = 1'),
            original.replace('component_depth = 2', 'component_depth = true'),
            original.replace('component_depth = 2', 'component_depth = 0'),
            original.replace('collected_at = "2026-01-01T00:00:00+00:00"', 'collected_at = "2026-01-01T00:00:00"'),
            original.replace('1001 =', '01001 ='),
            original.replace('1002 = "wi-1002"', '1002 = "wi-1001"'),
            original.replace('revision =', 'revision = "bad"\nrevision ='),
            original.replace('https://synthetic.invalid/tfs', 'http://localhost:8765'),
            original.replace('instance_alias = "ecl-synthetic"', 'instance_alias = "github_pat_PRIVATE_SECRET_SENTINEL"'),
            original.replace('include_changes', 'bogus') + '\n[limits]\npage_size = true',
            original.replace('project = "' + PROJECT + '"', 'project = false'),
            '# ' + 'a' * 1_048_576,
        )
        for contents in mutations:
            with self.subTest(contents=contents[:80]):
                code, out, err, transport, get = self.invoke(contents, options=('--approve-publication',), tty=True)
                self.assertEqual((code, out), (2, ''))
                transport.assert_not_called(); get.assert_not_called()
                self.assertEqual(err, 'continuity: invalid or unapproved Azure connection configuration\n')

    def test_empty_and_interrupted_prompts_are_sanitized(self):
        self.assertEqual(self.invoke(options=('--approve-publication',), tty=True, prompt='')[0], 2)
        for exc in (EOFError('PRIVATE_SECRET_SENTINEL'), KeyboardInterrupt(), OSError('PRIVATE_SECRET_SENTINEL')):
            with patch('continuity.azure_connection.getpass.getpass', side_effect=exc):
                # invoke's nested prompt mock is deliberately avoided here.
                with patch('continuity.azure_connection.sys.stdin.isatty', return_value=True), \
                     patch('continuity.azure_connection.AzureHttpTransport') as transport, \
                     redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
                    code = main(['azure-acquire', '--config', str(EXAMPLE), '--approve-publication'])
                self.assertEqual((code, out.getvalue()), (2, ''))
                self.assertNotIn('PRIVATE_SECRET_SENTINEL', err.getvalue()); transport.assert_not_called()

    def test_getpass_warning_fallback_is_refused(self):
        def fallback(*args):
            warnings.warn('PRIVATE_SECRET_SENTINEL', getpass.GetPassWarning)
            return 'secret'
        with patch('continuity.azure_connection.getpass.getpass', side_effect=fallback), \
             patch('continuity.azure_connection.sys.stdin.isatty', return_value=True), \
             patch('continuity.azure_connection.AzureHttpTransport') as transport, \
             redirect_stderr(StringIO()) as err:
            code = main(['azure-acquire', '--config', str(EXAMPLE), '--approve-publication'])
        self.assertEqual(code, 2); transport.assert_not_called()
        self.assertNotIn('PRIVATE_SECRET_SENTINEL', err.getvalue())

    def test_missing_file_and_raw_processing_error_are_sanitized(self):
        with redirect_stderr(StringIO()) as err:
            self.assertEqual(main(['azure-acquire', '--config', '/PRIVATE_PATH_SENTINEL/missing', '--approve-publication', '--anonymous']), 2)
        self.assertNotIn('PRIVATE_PATH_SENTINEL', err.getvalue())
        with patch('continuity.azure_connection.traceability_to_json', side_effect=ValueError('PRIVATE_SECRET_SENTINEL')):
            code, out, err, _, _ = self.invoke()
        self.assertEqual((code, out), (2, '')); self.assertNotIn('PRIVATE_SECRET_SENTINEL', err)

    def test_invalid_azure_arguments_never_echo_values(self):
        for arguments in (
            ['--pat', 'PRIVATE_SECRET_SENTINEL'],
            ['--unknown', 'PRIVATE_SECRET_SENTINEL'],
            ['--config', '/PRIVATE_PATH_SENTINEL/c.toml', '--anonymous=PRIVATE_SECRET_SENTINEL'],
            [],
        ):
            with patch('continuity.azure_connection.AzureHttpTransport') as transport, \
                 patch('continuity.azure_connection.getpass.getpass') as get, \
                 redirect_stderr(StringIO()) as err, redirect_stdout(StringIO()) as out:
                code = main(['azure-acquire', *arguments])
            self.assertEqual((code, out.getvalue()), (2, ''))
            self.assertEqual(err.getvalue(), 'continuity: invalid Azure command arguments\n')
            transport.assert_not_called(); get.assert_not_called()
