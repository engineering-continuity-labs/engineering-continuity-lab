"""v0.4 AC401–418: executable synthetic evidence, not real test execution."""
from dataclasses import replace
from datetime import timedelta, timezone
import json
import unittest

from continuity.analysis.verification import derive, snapshot_for
from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import Direction as D, TraceStatus as TS, TraceabilityCapability as C
from continuity.domain.verification import Association, Kind as K, Limits, Lookup, Outcome, Reference, Relation as R
from continuity.reporting.verification import to_dict, to_json
from continuity.reporting.traceability import validate_report_envelope
from continuity.traceability_providers.verification_synthetic import fixture


class VerificationEvidenceTests(unittest.TestCase):
    def test_base_oracle_and_original_paths_are_actual_evidence(self):
        evidence=fixture();report=derive(evidence)
        self.assertEqual([(m.numerator,m.denominator) for m in report.metrics],[(2,4)]*4)
        self.assertEqual(dict(report.outcomes),dict.fromkeys(Outcome,1))
        self.assertEqual({r.reference.identifier for r in report.requirements if r.implementation==TS.VERIFIED},{'Q1','Q2'})
        self.assertTrue(report.snapshot_valid)
        for projection in report.projections:
            self.assertIn(projection.code_path,evidence.code.paths)
            self.assertEqual(projection.association.target,projection.code_path.nodes[0])
            self.assertLessEqual(len(projection.code_path.nodes)+1,6)
        self.assertEqual(to_dict(report)['schema_version'],'v0.4-demo-1')

    def test_typed_versioned_identity_and_relation_grammar(self):
        evidence=fixture();q=next(a for a in evidence.artifacts if a.kind==K.REQUIREMENT)
        self.assertNotEqual(q,replace(q,version='v2'))
        self.assertNotEqual(q,replace(q,scope='different-project'))
        self.assertNotEqual(q,replace(q,kind=K.TEST))
        a=evidence.associations[0]
        for bad in (lambda:replace(a,relation=R.TEST_REQUIREMENT),lambda:replace(a,source=replace(a.source,scope='other-project')),
                    lambda:replace(q,kind='FUTURE'),lambda:replace(q,version=''),lambda:replace(q,document_kind='ADR')):
            with self.assertRaises(ValueError):bad()

    def test_snapshot_digest_alias_scope_revision_qualification(self):
        evidence=fixture()
        self.assertEqual(snapshot_for(evidence.code,evidence.snapshot.alias),evidence.snapshot)
        for field,value in [('fingerprint','0'*64),('repository','another-repo'),('revision','e'*40)]:
            report=derive(replace(evidence,snapshot=replace(evidence.snapshot,**{field:value})))
            self.assertFalse(report.snapshot_valid)
            self.assertEqual(report.metrics[0].numerator,0);self.assertIsNone(report.metrics[0].value)
            self.assertIsNone(report.metrics[-1].value)
            self.assertTrue(all(not r.qualified for r in report.runs))
            self.assertEqual(report.metrics[1].numerator,2) # independent declared test links retained
        foreign=replace(evidence.associations[0].target,identifier='unobserved-wi')
        report=derive(replace(evidence,associations=(replace(evidence.associations[0],target=foreign),*evidence.associations[1:])))
        self.assertTrue(any(d.reason=='UNRESOLVED_ASSOCIATION' for d in report.diagnostics))
        self.assertNotIn(foreign,[p.association.target for p in report.projections])

    def test_execution_is_separate_from_test_links_and_all_outcomes(self):
        report=derive(fixture())
        self.assertEqual(report.metrics[1].numerator,2)
        self.assertEqual(report.metrics[-1].numerator,2)
        self.assertEqual(sum(dict(report.outcomes).values()),4)
        missing=derive(replace(fixture(),runs=()))
        self.assertEqual(missing.metrics[-1].numerator,0)
        self.assertEqual(missing.metrics[1].numerator,2)
        stale=derive(fixture('STALE_TARGET'))
        self.assertEqual(stale.metrics[-1].numerator,0)
        self.assertTrue(all(not r.qualified and r.reason=='TARGET_MISMATCH' for r in stale.runs))
        self.assertEqual(sum(dict(stale.outcomes).values()),0)
        e=fixture();wrong=replace(e.runs[0],test=replace(e.runs[0].test,version='v2'))
        report=derive(replace(e,runs=(wrong,*e.runs[1:])))
        self.assertTrue(any(r.reason=='UNOBSERVED_TEST_VERSION' for r in report.runs))

    def test_conflicts_quarantine_without_latest_pass_and_distinct_runs_remain(self):
        e=fixture();conflict=derive(fixture('CONFLICTING_RUN'))
        self.assertNotIn(e.runs[0].reference,[r.run.reference for r in conflict.runs])
        self.assertTrue(any(d.reason=='CONFLICTING_OBSERVATION' for d in conflict.diagnostics))
        self.assertIsNone(conflict.metrics[-1].value)
        different=replace(e.runs[0],reference=replace(e.runs[0].reference,identifier='V5'),outcome=Outcome.FAIL)
        association=Association(different.reference,different.test,R.VERIFICATION_TEST,e.boundary)
        lookup=Lookup(different.reference,R.VERIFICATION_TEST)
        report=derive(replace(e,runs=(*e.runs,different),associations=(*e.associations,association),lookups=(*e.lookups,lookup)))
        self.assertEqual(report.metrics[-1].numerator,2)
        self.assertEqual(dict(report.outcomes)[Outcome.FAIL],2)
        self.assertTrue(any(r.run==different and r.qualified for r in report.runs))

    def test_missing_requires_complete_supported_lookup_and_positive_partial_survives(self):
        base=derive(fixture());q4=next(r for r in base.requirements if r.reference.identifier=='Q4')
        self.assertEqual(q4.tests,TS.MISSING)
        partial=derive(fixture('PARTIAL'))
        self.assertEqual(partial.metrics[1].numerator,2)
        self.assertEqual(next(r for r in partial.requirements if r.reference.identifier=='Q4').tests,TS.PARTIAL)
        unsupported=derive(fixture('UNSUPPORTED'))
        self.assertIsNone(unsupported.metrics[1].value)
        self.assertEqual(next(r for r in unsupported.requirements if r.reference.identifier=='Q4').tests,TS.UNAVAILABLE)
        e=fixture();no_lookup=derive(replace(e,lookups=tuple(l for l in e.lookups if l.relation!=R.TEST_REQUIREMENT)))
        self.assertIsNone(no_lookup.metrics[1].value)
        self.assertEqual(next(r for r in no_lookup.requirements if r.reference.identifier=='Q4').tests,TS.UNAVAILABLE)

    def test_review_population_unavailability_cannot_certify_missing(self):
        e=fixture()
        for kind,field in ((K.TEST,'tests'),(K.ARCHITECTURE_DOCUMENT,'architecture'),(K.REQUIREMENT,'implementation')):
            for status,capability,expected in ((S.COMPLETE,C.UNSUPPORTED,TS.UNAVAILABLE),(S.FAILED,C.SUPPORTED,TS.UNAVAILABLE),(S.PARTIAL,C.SUPPORTED,TS.PARTIAL)):
                lookups=tuple(replace(l,status=status,capability=capability) if l.population==kind else l for l in e.lookups)
                report=derive(replace(e,lookups=lookups))
                q4=next(r for r in report.requirements if r.reference.identifier=='Q4')
                self.assertEqual(getattr(q4,field),expected)
                self.assertEqual(report.metrics[1].numerator,2)
                self.assertEqual(report.metrics[2].numerator,2)

    def test_review_unqualified_code_boundaries_preserve_independent_links(self):
        e=fixture();boundary=e.code.evidence.boundaries[0]
        for boundaries in ((replace(boundary,revision=None),),(boundary,replace(boundary,identifier='unknown-revision',revision=None)),(boundary,replace(boundary,identifier='conflicting-revision',revision='e'*40))):
            code=replace(e.code,evidence=replace(e.code.evidence,boundaries=boundaries))
            report=derive(replace(e,code=code))
            self.assertFalse(report.snapshot_valid)
            self.assertIsNone(report.metrics[0].value)
            self.assertIsNone(report.metrics[-1].value)
            self.assertEqual(report.metrics[1].numerator,2)
            self.assertEqual(report.metrics[2].numerator,2)
            self.assertTrue(all(not r.qualified for r in report.runs))

    def test_review_parallel_support_origins_preserve_exact_provenance(self):
        from continuity.analysis.traceability import derive as code_derive
        from continuity.traceability_providers.synthetic import base_fixture
        from continuity.domain.traceability import TraceLinkType,TraceLinkOrigin
        from continuity.reporting.traceability import trace_path_to_dict
        e=fixture();raw=base_fixture()
        link=next(l for l in raw.links if l.type==TraceLinkType.COMMIT_PATH and l.origin==TraceLinkOrigin.DIRECT_SOURCE_LINK)
        alternate=replace(link,origin=TraceLinkOrigin.DIRECT_PROVIDER_LINK,observations=tuple(replace(o,identifier='alternate-proof') for o in link.observations))
        code=code_derive(replace(raw,links=(*raw.links,alternate)))
        snapshot=snapshot_for(code,e.snapshot.alias)
        collection=replace(e,code=code,snapshot=snapshot,runs=tuple(replace(r,target=snapshot) for r in e.runs))
        report=derive(collection);wire=to_dict(report)
        self.assertEqual(len(report.projections),10)
        for projection,serialized in zip(report.projections,wire['paths'],strict=True):
            self.assertEqual(serialized['code_path'],trace_path_to_dict(projection.code_path))
        self.assertEqual(to_json(report),to_json(derive(replace(collection,associations=collection.associations[::-1]))))

    def test_empty_failed_and_measured_zero_are_distinct(self):
        self.assertTrue(all(m.value is None and m.denominator==0 for m in derive(fixture('EMPTY')).metrics))
        self.assertEqual(derive(fixture('FAILED')).collection.status,S.FAILED)
        e=fixture();no=derive(replace(e,associations=(),runs=()))
        self.assertEqual(no.metrics[1].value,0)
        self.assertEqual(no.metrics[1].status,TS.MISSING)

    def test_duplicates_and_permutations_are_byte_identical_including_timezone(self):
        e=fixture();expected=to_json(derive(e))
        for field in ('artifacts','associations','runs','lookups'):
            self.assertEqual(to_json(derive(replace(e,**{field:tuple(reversed(getattr(e,field)))}))),expected)
            self.assertEqual(to_json(derive(replace(e,**{field:getattr(e,field)*2}))),expected)
        zone=timezone(timedelta(hours=5,minutes=30))
        alternate=replace(e,collected_at=e.collected_at.astimezone(zone),runs=tuple(replace(r,observed_at=r.observed_at.astimezone(zone)) for r in e.runs))
        self.assertEqual(to_json(derive(alternate)),expected)

    def test_soft_hard_exact_limits_and_exhaustion_order(self):
        e=fixture();exact=replace(e,limits=Limits(len(e.artifacts),len(e.associations),len(e.runs),len(derive(e).projections)))
        self.assertEqual(derive(exact).collection.status,S.COMPLETE)
        limited=fixture('LIMIT');report=derive(limited)
        self.assertEqual(report.collection.status,S.PARTIAL)
        self.assertTrue(any(d.reason=='LIMIT_EXHAUSTED' for d in report.diagnostics))
        self.assertEqual(to_json(report),to_json(derive(replace(limited,artifacts=limited.artifacts[::-1],associations=limited.associations[::-1],runs=limited.runs[::-1]))))
        with self.assertRaises(ValueError):replace(e,artifacts=e.artifacts*1001)
        with self.assertRaises(ValueError):Limits(artifacts=True)
        conflict=replace(fixture('CONFLICTING_RUN'),limits=Limits(runs=1))
        self.assertTrue(any(d.reason=='CONFLICTING_OBSERVATION' for d in derive(conflict).diagnostics))
        self.assertNotIn(e.runs[0].reference,[r.run.reference for r in derive(conflict).runs])

    def test_privacy_sentinels_are_rejected_without_reflection(self):
        e=fixture();q=e.artifacts[0]
        for value in ('ghp_'+'A'*36,'github_pat_'+'B'*40,'TOKEN_SENTINEL','/Users/private/secret','https://private.invalid/path','cookie=SECRET'):
            with self.assertRaises(ValueError) as error:replace(q,identifier=value)
            self.assertNotIn(value,str(error.exception))
            with self.assertRaises(ValueError):replace(e.snapshot,alias=value)
        public=to_json(derive(e))
        self.assertNotIn('TOKEN_SENTINEL',public)
        self.assertTrue(json.loads(public)['synthetic'])

    def test_conflicting_lookups_cannot_restore_complete_negatives(self):
        e=fixture();lookup=next(l for l in e.lookups if l.endpoint and l.endpoint.identifier=='Q4' and l.relation==R.TEST_REQUIREMENT)
        report=derive(replace(e,lookups=(*e.lookups,replace(lookup,capability=C.UNKNOWN,status=S.PARTIAL))))
        self.assertIsNone(report.metrics[1].value)
        self.assertEqual(next(r for r in report.requirements if r.reference.identifier=='Q4').tests,TS.UNAVAILABLE)

    def test_demo_artifact_is_not_a_legacy_git_envelope(self):
        with self.assertRaises(ValueError):validate_report_envelope(to_dict(derive(fixture())))
        self.assertEqual(fixture(),fixture())
