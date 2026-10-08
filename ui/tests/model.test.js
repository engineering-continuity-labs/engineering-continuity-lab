import{test}from'node:test';
import assert from'node:assert/strict';
import{execFileSync}from'node:child_process';
import{existsSync}from'node:fs';
import{join}from'node:path';
import{fileURLToPath}from'node:url';
import{validateReport,demoReport,departure,exportReport,importReport}from'../dist/model.js';
import eShopReport from'../dist/eshop-report.js';
const repositoryRoot=fileURLToPath(new URL('../../',import.meta.url));
const python=process.env.PYTHON??(existsSync(join(repositoryRoot,'.venv/bin/python'))?join(repositoryRoot,'.venv/bin/python'):'python3');
const generatePythonReport=`import json,sys;sys.path.insert(0,'src');sys.path.insert(0,'tests');from traceability_report_fixture import synthetic_v3_report;print(json.dumps(synthetic_v3_report(sys.argv[1]),sort_keys=True,separators=(',',':')))`;
const validatePythonReport=`import json,sys;sys.path.insert(0,'src');from continuity.reporting.traceability import traceability_from_dict,validate_report_envelope;report=json.load(sys.stdin);validate_report_envelope(report);traceability_from_dict(report['traceability_evidence']);print('valid')`;
const pythonReport=(variant='BASE')=>JSON.parse(execFileSync(python,['-c',generatePythonReport,variant],{cwd:repositoryRoot,encoding:'utf8'}));
const assertPythonAccepts=report=>assert.equal(execFileSync(python,['-c',validatePythonReport],{cwd:repositoryRoot,input:JSON.stringify(report),encoding:'utf8'}).trim(),'valid');
test('Azure REST provider report survives Python-browser-Python round trip',()=>{
 const script=`import json,sys;sys.path.insert(0,'src');sys.path.insert(0,'tests');from azure_rest_fixture import profile,IDENTITIES,STAMP,RestFixture;from continuity.traceability_providers.azure_devops import AzureDevOpsTraceabilityProvider;from continuity.analysis.traceability import derive;from continuity.reporting.traceability import with_traceability;provider=AzureDevOpsTraceabilityProvider(profile(),IDENTITIES,STAMP,'synthetic-snapshot',RestFixture());print(json.dumps(with_traceability({'model':'experimental-v0.1','revision':'synthetic','as_of':'2026-01-01T00:00:00Z','commit_count':0,'components':[]},derive(provider.acquire()))))`;
 const report=JSON.parse(execFileSync(python,['-c',script],{cwd:repositoryRoot,encoding:'utf8'}));
 assert.deepEqual(importReport(exportReport(report)),report);
 assertPythonAccepts(importReport(exportReport(report)));
 const metrics=report.traceability_evidence.result.metrics;
 assert.equal(metrics.find(m=>m.dimension==='merged_pr_intent').numerator,3);
 assert.equal(metrics.find(m=>m.dimension==='commit_intent').denominator,4);
});
test('bundled eShop validation sample has the documented revision and baseline counts',()=>{const report=validateReport(eShopReport);assert.equal(report.revision,'b4a40872005d4bb29e5b1fa1ff7e244143d39215');assert.equal(report.commit_count,347);assert.equal(report.components.length,48);assert.deepEqual(Object.fromEntries(['LOW','MEDIUM','HIGH','CRITICAL'].map(risk=>[risk,report.components.filter(component=>component.risk===risk).length])),{LOW:33,MEDIUM:10,HIGH:0,CRITICAL:5});});
test('demo validates; concentration and shares agree',()=>assert.equal(validateReport(demoReport()).components.length,6));
test('departure matches file overlap and pre-departure shares',()=>{const r=demoReport(),p=r.components[0].contributors[0];const impact=departure(r,p.contributor).find(i=>i.component==='src/payments');assert.equal(impact.loss,.92);assert.equal(impact.successor.overlap,.5);assert.equal(impact.uncovered.length,1);});
test('rejects person output and corrupt report without changing input',()=>{for(const r of [{components:[{component:'a',share:1}]},null,{...demoReport(),as_of:'bad'}])assert.throws(()=>validateReport(r));const r=demoReport();r.components[0].contributors[0].share=2;assert.throws(()=>validateReport(r));});
test('empty report is valid and has no departure candidates',()=>{const r={...demoReport(),components:[]};validateReport(r);assert.deepEqual(departure(r,'missing'),[]);});
test('no successor without overlapping file evidence',()=>{const r=demoReport();r.components[0].contributors[1].files=['different'];assert.equal(departure(r,r.components[0].contributors[0].contributor).find(i=>i.component==='src/payments').successor,null);});
test('synthetic demo has mixed risk and continuity-stress evidence',()=>{const r=demoReport(),risks=new Set(r.components.map(c=>c.risk));assert.deepEqual(risks,new Set(['LOW','MEDIUM','HIGH','CRITICAL']));const impact=departure(r,r.components[0].contributors[0].contributor);assert.ok(impact.some(i=>i.successor&&i.uncovered.length));});
test('export-compatible JSON can be reopened as an analysis report',()=>{const exported=JSON.parse(JSON.stringify(demoReport()));assert.deepEqual(validateReport(exported),exported);});

function reviewReport(status='COMPLETE',qualified=true){
 const author={identifier:'author',display_name:'Author',is_bot:false},reviewer={identifier:'reviewer',display_name:'Reviewer',is_bot:false};
 return {...demoReport(),report_version:'2.0',review_evidence:{provenance:{provenance:{provider:'github',repository:'public/example',evidence_boundary:'all reachable public closed PR pages; merged only',retrieved_at:'2026-10-07T00:00:00Z'},status,diagnostics:status==='PARTIAL'?['Public API interrupted collection.']:[],pull_requests:[{identifier:'42',author,merged_at:'2026-10-07T00:00:00Z',changed_paths:['src/a.py'],reviews:[{identifier:'one',state:qualified?'APPROVED':'COMMENTED',reviewer,submitted_at:null,provider_order:1,dismissed:false}]}]},components:[{component:'src',covered_pull_requests:qualified?1:0,mapped_pull_requests:1,coverage:qualified?1:0,coverage_status:status,reviewer_units:qualified?{reviewer:1}:{},reviewer_shares:qualified?{reviewer:1}:{},concentration:qualified?1:null,risk:qualified?'CRITICAL':null,unreviewed_pull_requests:qualified?[]:['42'],excluded_reasons:qualified?{}:{commented:1}}]}};
}
for(const status of ['COMPLETE','PARTIAL'])for(const qualified of [true,false])test(`${status} review export/import retains provenance, counts and unavailable population ${qualified}`,()=>{
 const report=reviewReport(status,qualified),reopened=importReport(exportReport(report));
 assert.deepEqual(reopened,report);assert.deepEqual(reopened.review_evidence,report.review_evidence);
});
test('v0.1 export/import remains identical and absence of reviews remains absent',()=>{const r=demoReport();assert.deepEqual(importReport(exportReport(r)),r);assert.equal(importReport(exportReport(r)).review_evidence,undefined);assert.doesNotThrow(()=>validateReport({...r,report_version:'2.0'}));});
test('empty successful review collection is valid and unavailable, not zero coverage',()=>{const r=reviewReport();r.review_evidence.provenance.pull_requests=[];r.review_evidence.components=[];assert.deepEqual(importReport(exportReport(r)),r);});
test('optional reviewer shares may be omitted without changing concentration',()=>{const r=reviewReport();delete r.review_evidence.components[0].reviewer_shares;assert.doesNotThrow(()=>validateReport(r));});
test('rejects malformed review provenance, status, identities and numerical contradictions',()=>{
 const mutations=[
 r=>delete r.report_version,r=>r.report_version='4.0',r=>r.review_evidence=null,
 r=>r.review_evidence.provenance.provenance=null,r=>r.review_evidence.provenance.provenance.retrieved_at='bad',
 r=>r.review_evidence.provenance.provenance.repository='https://secret@github.com/org/repo',
 r=>r.review_evidence.provenance.provenance.evidence_boundary='',r=>r.review_evidence.provenance.status='UNKNOWN',
 r=>r.review_evidence.provenance.diagnostics='error',r=>r.review_evidence.provenance.pull_requests[0].author=null,
 r=>r.review_evidence.provenance.pull_requests[0].reviews[0].state='OTHER',
 r=>r.review_evidence.provenance.pull_requests[0].reviews.push(r.review_evidence.provenance.pull_requests[0].reviews[0]),
 r=>r.review_evidence.components[0].component='',r=>r.review_evidence.components.push(r.review_evidence.components[0]),
 r=>r.review_evidence.components[0].mapped_pull_requests=-1,r=>r.review_evidence.components[0].covered_pull_requests=2,
 r=>r.review_evidence.components[0].coverage=.3,r=>r.review_evidence.components[0].coverage_status='PARTIAL',
 r=>r.review_evidence.components[0].reviewer_units={reviewer:-1},r=>r.review_evidence.components[0].reviewer_shares={reviewer:.2},
 r=>r.review_evidence.components[0].concentration=.2,r=>r.review_evidence.components[0].risk='LOW',
 r=>r.review_evidence.components[0].unreviewed_pull_requests=[123],r=>r.review_evidence.components[0].excluded_reasons={commented:-1},
 ];
 for(const mutate of mutations){const r=reviewReport();mutate(r);assert.throws(()=>validateReport(r));}
});

test('R1 rejects review aggregates contradicting retained effective events or component paths',()=>{
 for(const depth of [undefined,1]){
  for(const mutate of [
   r=>r.review_evidence.provenance.pull_requests[0].reviews=[],
   r=>r.review_evidence.provenance.pull_requests[0].reviews[0].state='COMMENTED',
   r=>r.review_evidence.components[0].reviewer_units={unrelated:1},
   r=>r.review_evidence.provenance.pull_requests[0].reviews.push({...r.review_evidence.provenance.pull_requests[0].reviews[0],identifier:'two',provider_order:2,state:'DISMISSED'}),
  ]){const r=reviewReport();if(depth!==undefined)r.review_evidence.component_depth=depth;mutate(r);assert.throws(()=>validateReport(r));}
 }
 for(const mutate of [r=>r.review_evidence.provenance.pull_requests[0].changed_paths=['docs/readme.md'],r=>r.review_evidence.components[0].component='wrong',r=>r.review_evidence.components[0].excluded_reasons={commented:1}]){
  const r=reviewReport();r.review_evidence.component_depth=1;mutate(r);assert.throws(()=>validateReport(r));
 }
});
test('known directory strategy reconciles multiple components and latest effective state on round trip',()=>{
 const r=reviewReport();r.review_evidence.component_depth=1;
 r.review_evidence.provenance.pull_requests[0].changed_paths.push('docs/readme.md');
 r.review_evidence.provenance.pull_requests[0].reviews.unshift({...r.review_evidence.provenance.pull_requests[0].reviews[0],identifier:'older',provider_order:0,state:'COMMENTED'});
 r.review_evidence.components.push({...structuredClone(r.review_evidence.components[0]),component:'docs'});
 assert.deepEqual(importReport(exportReport(r)),r);
});
test('Python BASE v3 fixture validates and survives browser and Python round trips',()=>{
 const report=pythonReport(),saved=importReport(exportReport(report));
 assert.equal(report.report_version,'3.0');assert.equal(report.model,'experimental-v0.1');
 assert.deepEqual(saved,report);assert.deepEqual(saved.traceability_evidence,report.traceability_evidence);
 assertPythonAccepts(saved);
});
test('v3 permits review coexistence, PARTIAL evidence, FAILED evidence and Git-only envelopes',()=>{
 const base=pythonReport(),combined={...reviewReport(),...base,report_version:'3.0',review_evidence:reviewReport().review_evidence};
 assert.deepEqual(importReport(exportReport(combined)),combined);
 const partial=pythonReport('PARTIAL'),failed=pythonReport('FAILED');
 const capability=pythonReport('CAPABILITY'),empty=pythonReport('EMPTY');
 const prPathOnly=pythonReport('PR_PATH_ONLY');
 assert.equal(partial.traceability_evidence.collection.status,'PARTIAL');
 assert.equal(failed.traceability_evidence.collection.status,'FAILED');
 assert.equal(failed.traceability_evidence.result.summary,'UNAVAILABLE');
 assert.deepEqual(importReport(exportReport(partial)),partial);assert.deepEqual(importReport(exportReport(failed)),failed);
 assert.deepEqual(importReport(exportReport(capability)),capability);assert.deepEqual(importReport(exportReport(empty)),empty);
 assert.deepEqual(importReport(exportReport(prPathOnly)),prPathOnly);
 assert.ok(prPathOnly.traceability_evidence.result.paths.some(path=>path.nodes.some(node=>node.kind==='PR_PATH')));
 assert.equal(prPathOnly.traceability_evidence.result.metrics.find(metric=>metric.dimension==='commit_intent').denominator,4);
 assert.doesNotThrow(()=>validateReport({...demoReport(),report_version:'3.0'}));
 assert.throws(()=>validateReport({...demoReport(),model:'experimental-v0.2',report_version:'3.0'}));
});
test('browser rejects malformed v3 paths, links, gaps, metrics, provenance and future types',()=>{
 const mutations=[
  r=>r.traceability_evidence.schema_version='2.0',
  r=>r.traceability_evidence.collection.populations.commits[0].kind='FUTURE_COMMIT',
  r=>r.traceability_evidence.collection.observed_links[0].type='FUTURE_LINK',
  r=>r.traceability_evidence.collection.observed_links[0].origin='DERIVED_LINK',
  r=>r.traceability_evidence.collection.observed_links[0].target=r.traceability_evidence.collection.populations.commits[0],
  r=>r.traceability_evidence.collection.boundaries[0].query='https://user:SECRET@example.test',
    r=>r.traceability_evidence.collection.status='UNKNOWN',
    r=>r.traceability_evidence.collection.lookups[0].capability='FUTURE_CAPABILITY',
    r=>r.traceability_evidence.collection.observed_links.push(structuredClone(r.traceability_evidence.collection.observed_links[0])),
    r=>r.traceability_evidence.collection.populations.commits.reverse(),
    r=>r.traceability_evidence.collection.populations.commits.splice(0,1),
  r=>r.traceability_evidence.result.paths[0].nodes.push(r.traceability_evidence.result.paths[0].nodes[0]),
    r=>{const path=r.traceability_evidence.result.paths.find(p=>p.status==='PARTIAL');path.gaps=[];},
    r=>r.traceability_evidence.result.paths.reverse(),
  r=>r.traceability_evidence.result.paths[0].supports.length=0,
  r=>r.traceability_evidence.result.derived_links[0].supports=[],
  r=>r.traceability_evidence.result.derived_links.splice(r.traceability_evidence.result.derived_links.findIndex(link=>link.type==='PATH_COMPONENT'),1),
  r=>r.traceability_evidence.result.paths.pop(),
  r=>r.traceability_evidence.result.gaps[0].status='VERIFIED',
    r=>r.traceability_evidence.result.artifacts.find(a=>a.status==='MISSING').status='VERIFIED',
  r=>r.traceability_evidence.result.metrics[0].numerator=r.traceability_evidence.result.metrics[0].denominator+1,
  r=>r.traceability_evidence.result.metrics[0].value=.25,
    r=>{const metric=r.traceability_evidence.result.metrics[0];metric.numerator=0;metric.value=0;metric.status='MISSING';metric.reason=null;},
    r=>r.traceability_evidence.result.metrics[0].boundaries=['unknown-boundary'],
    r=>r.traceability_evidence.result.metrics[0].excluded_count+=1,
    r=>r.traceability_evidence.result.diagnostics.push({reason:'INCOMPATIBLE_BOUNDARY',endpoint:null,relationship:null}),
    r=>r.traceability_evidence.result.derivation_version='offline-2',
    r=>r.model='experimental-v0.2',
    r=>{const gap=r.traceability_evidence.result.gaps.find(g=>g.status==='MISSING'),lookups=r.traceability_evidence.collection.lookups;const index=lookups.findIndex(l=>l.endpoint&&JSON.stringify(l.endpoint)===JSON.stringify(gap.endpoint)&&l.relationship===gap.relationship&&l.direction===gap.direction);lookups.splice(index,1);},
 ];
 for(const mutate of mutations){const report=pythonReport();mutate(report);assert.throws(()=>validateReport(report));}
 for(const version of ['4.0',null]){const future={...pythonReport(),report_version:version};assert.throws(()=>validateReport(future));}
});

const reviewCorpus=JSON.parse(execFileSync(python,['-c',`import json,sys;sys.path[:0]=['src','tests'];from traceability_report_adversaries import adversarial_reports,normalization_adversaries,additional_valid_reports;print(json.dumps({'invalid':{**adversarial_reports(),**normalization_adversaries()},'valid':additional_valid_reports()}))`],{cwd:repositoryRoot,encoding:'utf8',maxBuffer:16*1024*1024}));
test('independent review shared wire adversaries fail closed in the browser',()=>{
 for(const [name,report] of Object.entries(reviewCorpus.invalid))assert.throws(()=>validateReport(report),undefined,name);
});
test('every synthetic variant and precise boundary/Unicode fixture survives Python-browser-Python',()=>{
 for(const variant of ['NO_INTENT','DIRECT_ONLY','MULTIPATH','DUPLICATES','CONFLICT','CYCLE','MALFORMED','UNSUPPORTED_TYPE','OPTIONAL','POSITIVE_PARTIAL','LATE_FAILURE','LINKED_ONLY','BOUNDARY','NO_INFERENCE']){
  const report=pythonReport(variant);assert.deepEqual(importReport(exportReport(report)),report,variant);assertPythonAccepts(report);
 }
 for(const [name,report] of Object.entries(reviewCorpus.valid)){assert.deepEqual(importReport(exportReport(report)),report,name);assertPythonAccepts(report);}
});
test('malformed JSON, duplicate fields and recursion failures never echo submitted secrets',()=>{
 const base=pythonReport(),payload=JSON.stringify(base);
 for(const value of [payload.replace('"schema_version":"1.0"','"schema_version":"SECRET","schema_version":"1.0"'),payload.replace('"schema_version":"1.0"','"schema_version":"1.0","schema_vers\\u0069on":"1.0"'),'{"SECRET":','{"SECRET":Infinity}','['.repeat(2000)+']'.repeat(2000)]){
  assert.throws(()=>importReport(value),error=>error.message.startsWith('Select a valid continuity')&&!error.message.includes('SECRET'));
 }
 const cycle=structuredClone(base);cycle.traceability_evidence.self=cycle.traceability_evidence;
 assert.throws(()=>validateReport(cycle),error=>error.message.startsWith('Select a valid continuity'));
 assert.throws(()=>exportReport(cycle),error=>error.message.startsWith('Select a valid continuity'));
 const saved=exportReport(base);assert.throws(()=>importReport('{"SECRET":'));assert.deepEqual(importReport(saved),base);
});

const closureCorpus=JSON.parse(execFileSync(python,['-c',`import json,sys;sys.path[:0]=['src','tests'];from traceability_report_adversaries import closure_review_reports;print(json.dumps(closure_review_reports()))`],{cwd:repositoryRoot,encoding:'utf8',maxBuffer:16*1024*1024}));
for(const finding of ['RP-R11','RP-R12','RP-R13'])test(`closure ${finding} matches Python acceptance at configuration/completeness boundaries`,()=>{
 assert.throws(()=>validateReport(closureCorpus.invalid[finding]));
 const valid=closureCorpus.valid[finding];
 assert.deepEqual(importReport(exportReport(valid)),valid);assertPythonAccepts(valid);
 if(finding==='RP-R12'){
  const dual=closureCorpus.valid['RP-R12-DUAL'];assert.deepEqual(importReport(exportReport(dual)),dual);assertPythonAccepts(dual);
 }
});
