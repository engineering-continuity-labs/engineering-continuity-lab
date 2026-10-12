"""AC426–429 source-derived product showcase, not hand-authored aggregates."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('generate_showcase',ROOT/'scripts/generate_showcase.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProductShowcaseTests(unittest.TestCase):
    def test_source_derived_exact_review_oracle_and_different_patterns(self):
        show=module.showcase();review=show['report']['review_evidence'];rows={c['component']:c for c in review['components']}
        payments=rows['src/payments']
        self.assertEqual((payments['mapped_pull_requests'],payments['covered_pull_requests']),(4,3))
        self.assertEqual(payments['reviewer_units'],{'reviewer-alpha':2,'reviewer-beta':1})
        self.assertAlmostEqual(payments['coverage'],.75)
        self.assertAlmostEqual(payments['concentration'],5/9)
        self.assertEqual(payments['risk'],'MEDIUM')
        self.assertEqual(payments['unreviewed_pull_requests'],('54',))
        self.assertEqual(payments['excluded_reasons'],{'self_review':1,'provider_declared_bot':1,'commented':2})
        self.assertEqual(rows['tests/payments']['concentration'],1)
        self.assertIsNone(rows['src/identity']['concentration'])
        prs=review['provenance']['pull_requests'];self.assertEqual(len(prs),6)
        self.assertGreater(len({pr['author']['identifier'] for pr in prs}),1)
        states={e['state'] for pr in prs for e in pr['reviews']}
        self.assertTrue({'APPROVED','CHANGES_REQUESTED','COMMENTED'}<=states)
        self.assertTrue(any(len(pr['changed_paths'])>1 for pr in prs))
        self.assertTrue(any(len([e for e in pr['reviews'] if e['reviewer'] and e['reviewer']['identifier']=='reviewer-alpha'])>1 for pr in prs))

    def test_same_showcase_code_snapshot_and_verification_oracle(self):
        show=module.showcase();v=show['verification'];r=show['report']
        self.assertEqual(v['code_traceability'],r['traceability_evidence'])
        self.assertEqual(r['revision'],v['snapshot']['revision'])
        self.assertEqual([(m['numerator'],m['denominator']) for m in v['metrics']],[(2,4)]*4)
        self.assertEqual(v['outcomes'],dict(PASS=1,FAIL=1,SKIPPED=1,UNKNOWN=1))
        self.assertEqual({c['component'] for c in r['components']},{'src/payments','src/catalog','src/orders','src/identity','tests/payments','tests/orders'})
        self.assertEqual(r['report_version'],'3.0')
        self.assertTrue(v['synthetic'])

    def test_generated_showcase_is_deterministic_and_fresh(self):
        self.assertEqual(module.generate(),module.generate())
        self.assertEqual((ROOT/'ui/dist/showcase.js').read_text(),module.generate())
