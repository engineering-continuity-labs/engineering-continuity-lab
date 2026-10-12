"""AC432–437 genuine v3 + manifest through portable report boundaries."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from continuity.reporting.portable import (collection_to_dict, manifest_from_json, with_verification_evidence,
                                           report_to_json, report_from_json, loads, canonical)
from continuity.traceability_providers.verification_synthetic import fixture
from continuity.reporting.traceability import traceability_to_dict
from traceability_report_fixture import synthetic_v3_report


def portable(variant='BASE'):
    e=fixture(variant)
    legacy=synthetic_v3_report('BASE')
    legacy['traceability_evidence']=traceability_to_dict(e.code)
    legacy['revision']=e.code.evidence.boundaries[0].revision
    manifest={'manifest_version':'1.0','publication_approved':True,'collection':collection_to_dict(e)}
    parsed=manifest_from_json(canonical(manifest),e.code)
    return with_verification_evidence(legacy,parsed),manifest,legacy


def expanded_collections():
    from continuity.domain.verification import Association,Kind as K,Relation as R,Outcome
    from continuity.domain.reviews import CollectionStatus as S
    from continuity.domain.traceability import Direction as D
    from continuity.analysis.verification import snapshot_for
    from continuity.analysis.traceability import derive as code_derive
    from continuity.traceability_providers.synthetic import SyntheticTraceabilityProvider
    e=fixture();q=next(a for a in e.artifacts if a.kind==K.REQUIREMENT);t=e.runs[0].test
    doc=next(a for a in e.artifacts if a.kind==K.ARCHITECTURE_DOCUMENT)
    new_run=replace(e.runs[0],reference=replace(e.runs[0].reference,identifier='V5'),outcome=Outcome.FAIL)
    extra=Association(new_run.reference,new_run.test,R.VERIFICATION_TEST,e.boundary)
    multiple=replace(e,runs=(*e.runs,new_run),associations=(*e.associations,extra),lookups=(*e.lookups,*[replace(l,endpoint=new_run.reference) for l in e.lookups if l.endpoint==e.runs[0].reference]))
    short_code=code_derive(SyntheticTraceabilityProvider('PR_PATH_ONLY').acquire());short_snapshot=snapshot_for(short_code,e.snapshot.alias)
    return {
        'LATE_FAILURE':replace(e,status=S.PARTIAL),
        'WRONG_SCOPE':replace(e,artifacts=tuple(replace(a,scope='other-project') if a.kind==K.REQUIREMENT else a for a in e.artifacts)),
        'STALE_REVISION':replace(e,snapshot=replace(e.snapshot,revision='e'*40)),
        'WRONG_TEST_VERSION':replace(e,runs=(replace(e.runs[0],test=replace(t,version='v2')),*e.runs[1:])),
        'WRONG_TEST_TARGET':fixture('STALE_TARGET'),
        'UNLINKED_POPULATIONS':replace(e,associations=(),runs=()),
        'LINKED_ONLY':replace(e,artifacts=tuple(a for a in e.artifacts if a!=q)),
        'DUPLICATES':replace(e,artifacts=e.artifacts*2,associations=e.associations*2,runs=e.runs*2,lookups=e.lookups*2),
        'MULTIPLE_RUNS':multiple,
        'SHORT_CODE_PATH':replace(e,code=short_code,snapshot=short_snapshot,runs=tuple(replace(r,target=short_snapshot) for r in e.runs)),
        'REORDERED':replace(e,artifacts=e.artifacts[::-1],associations=e.associations[::-1],runs=e.runs[::-1],lookups=e.lookups[::-1]),
        'UNKNOWN_WORK_ITEM':replace(e,associations=tuple(replace(a,target=replace(a.target,identifier='9999')) if a.relation==R.REQUIREMENT_WORK_ITEM else a for a in e.associations)),
        'UNKNOWN_COMPONENT':replace(e,associations=tuple(replace(a,target=replace(a.target,identifier='src/absent')) if a.relation==R.DOCUMENT_COMPONENT else a for a in e.associations)),
        'ZERO_DENOMINATOR':fixture('EMPTY'),
        'MISSING_TEST_LINK':replace(e,associations=tuple(a for a in e.associations if a.relation!=R.TEST_REQUIREMENT)),
        'TEST_LINK_WITHOUT_RUN':replace(e,runs=(),associations=tuple(a for a in e.associations if a.relation!=R.VERIFICATION_TEST)),
        'RUN_WITHOUT_SELECTED_TEST':replace(e,artifacts=tuple(a for a in e.artifacts if a!=t)),
        'DOCUMENT_WITHOUT_REQUIREMENT':replace(e,associations=tuple(a for a in e.associations if a.relation!=R.DOCUMENT_REQUIREMENT)),
        'DOCUMENT_COMPONENT_ONLY':replace(e,associations=tuple(a for a in e.associations if a.source.kind!=K.ARCHITECTURE_DOCUMENT or a.relation==R.DOCUMENT_COMPONENT)),
        'MULTIPLE_DOCUMENTS':replace(e,associations=(*e.associations,Association(doc,replace(q,identifier='Q2'),R.DOCUMENT_REQUIREMENT,e.boundary))),
        'MULTIPLE_TESTS_PER_REQUIREMENT':e,
        'PASS_AND_FAIL_DISTINCT_RUNS':multiple,
        'CONFLICTING_SAME_RUN_ID':fixture('CONFLICTING_RUN'),
    }


def expanded_reports():
    reports={}
    for name,e in expanded_collections().items():
        legacy=synthetic_v3_report('BASE');legacy['traceability_evidence']=traceability_to_dict(e.code)
        legacy['revision']=e.code.evidence.boundaries[0].revision
        manifest={'manifest_version':'1.0','publication_approved':True,'collection':collection_to_dict(e)}
        reports[name]=with_verification_evidence(legacy,manifest_from_json(canonical(manifest),e.code))
    return reports


class PortableEvidenceTests(unittest.TestCase):
    def test_actual_manifest_report_browser_python_base_oracle(self):
        report,manifest,legacy=portable()
        result=report['verification_evidence']['result']
        self.assertEqual([(m['numerator'],m['denominator']) for m in result['metrics']],[(2,4)]*4)
        self.assertEqual(result['outcomes'],dict(PASS=1,FAIL=1,SKIPPED=1,UNKNOWN=1))
        source=report_to_json(report)
        proc=subprocess.run(['node','--input-type=module','-e',"import {importReport,exportReport} from './ui/dist/model.js';let s='';for await(const c of process.stdin)s+=c;console.log(exportReport(importReport(s)));"],input=source,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(report_from_json(proc.stdout),report)
        self.assertEqual(legacy['report_version'],'3.0')

    def test_all_core_scenarios_roundtrip_and_input_order(self):
        for variant in ('BASE','PARTIAL','STALE_TARGET','CONFLICTING_RUN','EMPTY','UNSUPPORTED','FAILED','NO_LINKS','LIMIT'):
            with self.subTest(variant=variant):
                report,manifest,legacy=portable(variant)
                self.assertEqual(report_from_json(report_to_json(report)),report)
                raw=manifest['collection']
                for field in ('artifacts','associations','runs','lookups'):
                    raw[field].reverse()
                parsed=manifest_from_json(canonical(manifest),fixture().code)
                self.assertEqual(report_to_json(with_verification_evidence(legacy,parsed)),report_to_json(report))

    def test_full_named_matrix_through_manifest_browser_and_python(self):
        reports=expanded_reports()
        script="import {importReport,exportReport} from './ui/dist/model.js';let raw='';for await(const c of process.stdin)raw+=c;const reports=JSON.parse(raw);for(const [k,r] of Object.entries(reports))reports[k]=JSON.parse(exportReport(importReport(JSON.stringify(r))));console.log(JSON.stringify(reports));"
        proc=subprocess.run(['node','--input-type=module','-e',script],input=canonical(reports),text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        reopened=json.loads(proc.stdout)
        for name,report in reports.items():
            self.assertEqual(report_from_json(canonical(reopened[name])),report,name)
        self.assertEqual(next(m for m in reports['STALE_REVISION']['verification_evidence']['result']['metrics'] if m['dimension']=='requirement_implementation')['value'],None)
        multiple=reports['PASS_AND_FAIL_DISTINCT_RUNS']['verification_evidence']['result']
        self.assertEqual(multiple['outcomes']['FAIL'],2)
        self.assertEqual(next(m for m in multiple['metrics'] if m['dimension']=='executed_tests')['numerator'],2)

    def test_forged_results_unknown_schema_duplicates_and_privacy_reject(self):
        report,manifest,_=portable()
        bad=json.loads(canonical(report));bad['verification_evidence']['result']['outcomes']['PASS']=99
        with self.assertRaises(ValueError):report_from_json(canonical(bad))
        for change in ('future','private','duplicate'):
            bad=json.loads(canonical(report))
            if change=='future':bad['report_version']='5.0'
            if change=='private':bad['verification_evidence']['collection']['artifacts'][0]['identifier']='TOKEN_SENTINEL'
            if change=='duplicate':bad['verification_evidence']['collection']['artifacts']*=2
            with self.assertRaises(ValueError):report_from_json(canonical(bad))
        for approval in (False,None,'true',1):
            manifest['publication_approved']=approval
            with self.assertRaises(ValueError):manifest_from_json(canonical(manifest),fixture().code)
        for raw in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','"\\ud800"','['*65+'0'+']'*65):
            with self.assertRaises(ValueError):loads(raw)

    def test_v4_optional_sections_and_review_coexistence(self):
        from dataclasses import asdict
        from continuity.analysis.reviews import analyze_reviews
        from continuity.domain.models import DirectoryComponents
        from continuity.domain.reviews import ReviewState
        from test_review_evidence import collection,pull,event,ALICE
        report,_,legacy=portable()
        evidence=asdict(analyze_reviews(collection(pull('one',('src/a.py',),(event('review',ReviewState.APPROVED,ALICE),))),DirectoryComponents()))
        review=json.loads(json.dumps(evidence,default=lambda v:v.isoformat() if hasattr(v,'isoformat') else list(v)))
        report['review_evidence']=review
        self.assertEqual(report_from_json(report_to_json(report))['review_evidence'],review)
        bare={k:v for k,v in report.items() if k not in ('verification_evidence','traceability_evidence')}
        self.assertEqual(report_from_json(report_to_json(bare)),bare)
        for source in (report,bare):
            proc=subprocess.run(['node','--input-type=module','-e',"import {importReport} from './ui/dist/model.js';let s='';for await(const c of process.stdin)s+=c;importReport(s);"],input=report_to_json(source),text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr)

    def test_bounds_utf8_approval_unknown_privacy_and_cli_arguments(self):
        from continuity.reporting.portable import MAX_BYTES
        from continuity.offline_evidence import read_input
        report,manifest,_=portable()
        for field in ('native','title','description','person','reverse_mapping','logs','path'):
            bad=json.loads(canonical(manifest));bad['collection'][field]='PRIVATE_SENTINEL'
            with self.assertRaises(ValueError):manifest_from_json(canonical(bad),fixture().code)
        with self.assertRaises(ValueError):loads(b' '* (MAX_BYTES+1))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):read_input(root)
            import os
            fifo=root/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):read_input(fifo)
        proc=subprocess.run([sys.executable,'-m','continuity','evidence-attach','--TOKEN_SENTINEL'],text=True,capture_output=True)
        self.assertEqual(proc.returncode,2);self.assertEqual(proc.stdout,'');self.assertNotIn('TOKEN_SENTINEL',proc.stderr)

    def test_cli_success_and_fixed_nonreflecting_failures(self):
        report,manifest,legacy=portable()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);r=root/'v3.json';m=root/'manifest.json'
            r.write_text(canonical(legacy));m.write_text(canonical(manifest))
            command=[sys.executable,'-m','continuity','evidence-attach','--report',str(r),'--manifest',str(m)]
            proc=subprocess.run(command,text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(report_from_json(proc.stdout),report)
            for raw in (b'PRIVATE_SENTINEL{',b'\xff',b'{"publication_approved":false}'):
                m.write_bytes(raw);proc=subprocess.run(command,text=True,capture_output=True)
                self.assertEqual(proc.returncode,2);self.assertEqual(proc.stdout,'');self.assertNotIn('PRIVATE_SENTINEL',proc.stderr)


class PortableContractRegressionTests(unittest.TestCase):
    def browser(self, report):
        proc=subprocess.run(['node','--input-type=module','-e',"import {importReport,exportReport} from './ui/dist/model.js';let s='';for await(const c of process.stdin)s+=c;console.log(exportReport(importReport(s)));"],input=canonical(report),text=True,capture_output=True)
        return proc

    def test_toml_cli_output_is_exclusive_utf8_and_nonreflecting(self):
        from continuity.reporting.portable import manifest_from_toml
        raw=Path('examples/v0.4-evidence.toml').read_bytes()
        c=manifest_from_toml(raw,fixture().code)
        self.assertEqual(collection_to_dict(c),collection_to_dict(fixture()))
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'v4.json'
            command=[sys.executable,'-m','continuity','evidence-attach','--report','examples/v0.4-traceability-v3.json','--manifest','examples/v0.4-evidence.toml','--output',str(output)]
            proc=subprocess.run(command,text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(proc.stdout,'')
            report=report_from_json(output.read_bytes());self.assertEqual(report['report_version'],'4.0')
            previous=output.read_bytes();proc=subprocess.run(command,text=True,capture_output=True)
            self.assertEqual(proc.returncode,3);self.assertEqual(output.read_bytes(),previous);self.assertNotIn(d,proc.stderr)
            self.assertEqual(list(Path(d).iterdir()),[output])
        for bad in (raw+b'\nsecret = "TOKEN_SENTINEL"',raw.replace(b'publication_approved = true',b'publication_approved = false'),raw.replace(b'manifest_version = "1.0"',b'manifest_version = "1.0"\nmanifest_version = "1.0"'),raw.replace(b'collected_at = "2026-01-01T00:00:00+00:00"',b'collected_at = 2026-01-01T00:00:00Z'),b'\xff'):
            with self.assertRaises(ValueError):manifest_from_toml(bad,fixture().code)

    def test_v4_without_code_qualifies_no_current_execution(self):
        from continuity.reporting.portable import absent_code,verification_to_dict,validate_v4
        r,_,_=portable();r.pop('traceability_evidence')
        r['verification_evidence']=verification_to_dict(replace(fixture(),code=absent_code()))
        self.assertTrue(validate_v4(r))
        self.assertFalse(r['verification_evidence']['result']['snapshot_valid'])
        self.assertEqual(r['verification_evidence']['result']['outcomes'],dict(PASS=0,FAIL=0,SKIPPED=0,UNKNOWN=0))
        proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)

    def test_numeric_zero_roundtrip_limits_and_boolean_distinction(self):
        from continuity.reporting.portable import verification_to_dict
        e=replace(fixture(),runs=(),associations=tuple(a for a in fixture().associations if a.relation.value!='VERIFICATION_TEST'))
        r,_,_=portable();r['verification_evidence']=verification_to_dict(e)
        proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)
        r,_,_=portable();r['verification_evidence']['collection']['limits']['artifacts']=1000.0
        r['verification_evidence']['result']['outcomes']['PASS']=1.0
        self.assertTrue(report_from_json(canonical(r)));self.assertEqual(self.browser(r).returncode,0)
        r['verification_evidence']['result']['outcomes']['PASS']=True
        with self.assertRaises(ValueError):report_from_json(canonical(r))
        self.assertNotEqual(self.browser(r).returncode,0)

    def test_whole_envelope_privacy_unknown_fields_and_snapshot_reject_parity(self):
        import copy
        from continuity.reporting.portable import validate_v4
        base,_,_=portable()
        mutations=[lambda r:r.update(warning='TOKEN_SENTINEL'),lambda r:r.update(source='/Users/private/secret'),lambda r:r.update(source='C:\\private\\file'),lambda r:r.update(source='raw https://user:password@example.test'),lambda r:r.update(commit_count=9007199254740992),lambda r:r.update(as_of='2026-02-30T00:00:00Z'),lambda r:r.update(revision='e'*40),lambda r:r.update(configuration={'component_depth':3}),lambda r:r.update(extra='raw')]
        for mutate in mutations:
            r=copy.deepcopy(base);mutate(r)
            with self.assertRaises(ValueError):validate_v4(r)
            self.assertNotEqual(self.browser(r).returncode,0)
        r=copy.deepcopy(base);r['verification_evidence']['collection']['runs'][0]['target']['revision']='e'*40
        with self.assertRaises(ValueError):validate_v4(r) # unchanged derived result is forged

    def test_utc_timestamp_duplicates_and_permutations_canonicalize(self):
        r,m,legacy=portable();other=json.loads(canonical(m))
        for run in other['collection']['runs']:
            run['observed_at']=run['observed_at'].replace('2026-01-01T00:00:00+00:00','2026-01-01T01:00:00+01:00')
        e=manifest_from_json(canonical(other),fixture().code)
        self.assertEqual(report_to_json(with_verification_evidence(legacy,e)),report_to_json(r))

    def test_v4_unicode_review_identity_and_microsecond_order_parity(self):
        from dataclasses import asdict
        from datetime import timedelta
        from continuity.domain.reviews import ReviewIdentity,ReviewState
        from continuity.domain.models import DirectoryComponents
        from continuity.analysis.reviews import analyze_reviews
        from test_review_evidence import collection,pull,event,ALICE
        reviewer=ReviewIdentity('Straße')
        first=event('z-old',ReviewState.COMMENTED,reviewer)
        second=replace(event('a-new',ReviewState.APPROVED,reviewer),submitted_at=first.submitted_at+timedelta(microseconds=1))
        r,_,_=portable()
        review=asdict(analyze_reviews(collection(pull('unicode',('src/a.py',),(first,second))),DirectoryComponents()))
        r['review_evidence']=json.loads(json.dumps(review,default=lambda v:v.isoformat() if hasattr(v,'isoformat') else list(v)))
        proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)


    def test_pe_r01_malformed_toml_shapes_have_fixed_cli_errors(self):
        from continuity.reporting.portable import manifest_from_toml
        malformed=['manifest_version="1.0"\npublication_approved=true\ncollection=1\n',
                   'manifest_version="1.0"\npublication_approved=true\n[collection]\nruns=[1]\n']
        valid=Path('examples/v0.4-evidence.toml').read_text()
        import tomllib
        collection=tomllib.loads(valid)['collection']
        for name in ('runs','lookups','artifacts','associations'):
            broken=json.loads(canonical(collection));broken[name]=[1]
            # API shape checking through TOML with full required collection fields.
            import sys
            sys.path.insert(0,'scripts')
            from generate_portable_example import toml_value
            malformed.append('manifest_version="1.0"\npublication_approved=true\ncollection='+toml_value(broken))
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'PRIVATE_SENTINEL.toml'
            for raw in malformed:
                with self.assertRaisesRegex(ValueError,'^invalid or unapproved evidence manifest$'):
                    manifest_from_toml(raw,fixture().code)
                manifest.write_text(raw)
                proc=subprocess.run([sys.executable,'-m','continuity','evidence-attach','--report','examples/v0.4-traceability-v3.json','--manifest',str(manifest)],text=True,capture_output=True)
                self.assertEqual(proc.returncode,2);self.assertEqual(proc.stdout,'')
                self.assertEqual(proc.stderr,'continuity: invalid or unapproved offline evidence inputs\n')


    def test_pe_r02_extreme_review_float_order_and_boolean_counts(self):
        from dataclasses import asdict
        from datetime import datetime,timezone,timedelta
        from continuity.domain.reviews import ReviewIdentity,ReviewState
        from continuity.domain.models import DirectoryComponents
        from continuity.analysis.reviews import analyze_reviews
        from test_review_evidence import collection,pull,event
        reviewer=ReviewIdentity('reviewer')
        for year in (1,2026,9999):
            time=datetime(year,1,1,tzinfo=timezone.utc)
            first=replace(event('z-old',ReviewState.APPROVED,reviewer),submitted_at=time,provider_order=1)
            second=replace(event('a-new',ReviewState.COMMENTED,reviewer),submitted_at=time+timedelta(microseconds=1),provider_order=0)
            r,_,_=portable()
            review=asdict(analyze_reviews(collection(pull('rounded',('src/a.py',),(first,second))),DirectoryComponents()))
            r['review_evidence']=json.loads(json.dumps(review,default=lambda v:v.isoformat() if hasattr(v,'isoformat') else list(v)))
            proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)
        for field in ('mapped_pull_requests','covered_pull_requests'):
            bad=json.loads(canonical(r));bad['review_evidence']['components'][0][field]=True
            with self.assertRaises(ValueError):report_from_json(canonical(bad))
            self.assertNotEqual(self.browser(bad).returncode,0)


    def test_pe_r01_direct_section_errors_and_legacy_container_shapes_sanitized(self):
        from continuity.reporting.portable import verification_from_dict
        r,_,_=portable();r['verification_evidence']['collection']['runs'][0]['outcome']='TOKEN_SENTINEL'
        with self.assertRaisesRegex(ValueError,'^invalid portable evidence section$'):
            verification_from_dict(r['verification_evidence'],fixture().code)
        report=json.loads(Path('examples/v0.4-traceability-v3.json').read_text())
        report['components'][0]['contributors'][0]['file_activity']=[]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'PRIVATE_SENTINEL.json';source.write_text(canonical(report))
            proc=subprocess.run([sys.executable,'-m','continuity','evidence-attach','--report',str(source),'--manifest','examples/v0.4-evidence.toml'],text=True,capture_output=True)
            self.assertEqual(proc.returncode,2);self.assertEqual(proc.stdout,'');self.assertEqual(proc.stderr,'continuity: invalid or unapproved offline evidence inputs\n')
        report['report_version']='4.0'
        with self.assertRaisesRegex(ValueError,'^invalid portable evidence report$'):report_from_json(canonical(report))
        self.assertNotEqual(self.browser(report).returncode,0)

    def test_pe_r03_complete_unicode_folding_and_pe_r04_boolean_maps(self):
        from dataclasses import asdict
        from continuity.domain.reviews import ReviewIdentity,ReviewState
        from continuity.domain.models import DirectoryComponents
        from continuity.analysis.reviews import analyze_reviews
        from test_review_evidence import collection,pull,event
        r,_,_=portable()
        reviewer=ReviewIdentity('\u1c89')
        review=asdict(analyze_reviews(collection(pull('unicode-version',('src/a.py',),(event('approved',ReviewState.APPROVED,reviewer),))),DirectoryComponents()))
        r['review_evidence']=json.loads(json.dumps(review,default=lambda v:v.isoformat() if hasattr(v,'isoformat') else list(v)))
        proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)
        for field in ('reviewer_units','reviewer_shares','excluded_reasons'):
            bad=json.loads(canonical(r));bad['review_evidence']['components'][0][field]={reviewer.identifier:True}
            with self.assertRaises(ValueError):report_from_json(canonical(bad))
            self.assertNotEqual(self.browser(bad).returncode,0)


    def test_pe_r05_integral_git_numbers_and_numeric_canonical_spelling(self):
        r,_,_=portable();r['commit_count']=0.0
        proc=self.browser(r);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_from_json(proc.stdout),r)
        a=json.loads(canonical(r));b=json.loads(canonical(r));a['configuration']={'weights':{'recency':1}};b['configuration']={'weights':{'recency':1.0}}
        self.assertEqual(report_to_json(a),report_to_json(b))
        r['commit_count']=False
        with self.assertRaises(ValueError):report_from_json(canonical(r))
        self.assertNotEqual(self.browser(r).returncode,0)


    def test_pe_r06_equivalent_code_timestamp_spellings_attach(self):
        from continuity.reporting.traceability import traceability_from_dict
        r,m,legacy=portable()
        def rewire(value,suffix):
            if isinstance(value,str) and value.endswith('+00:00'):return value[:-6]+suffix
            if isinstance(value,list):return [rewire(v,suffix) for v in value]
            if isinstance(value,dict):return {k:rewire(v,suffix) for k,v in value.items()}
            return value
        for suffix in ('Z','.000000+00:00'):
            other=rewire(legacy,suffix);code=traceability_from_dict(other['traceability_evidence'])
            parsed=manifest_from_json(canonical(m),code)
            attached=with_verification_evidence(other,parsed)
            self.assertEqual(report_to_json(attached),report_to_json(r))
            proc=self.browser(attached);self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(report_to_json(report_from_json(proc.stdout)),report_to_json(attached))
            with tempfile.TemporaryDirectory() as d:
                source=Path(d)/'v3.json';source.write_text(canonical(other))
                command=[sys.executable,'-m','continuity','evidence-attach','--report',str(source),'--manifest','examples/v0.4-evidence.toml']
                proc=subprocess.run(command,text=True,capture_output=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                self.assertEqual(report_to_json(report_from_json(proc.stdout)),report_to_json(r))
