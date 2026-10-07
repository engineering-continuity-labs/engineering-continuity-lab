import{test}from'node:test';
import assert from'node:assert/strict';
import{validateReport,demoReport,departure,exportReport,importReport}from'../dist/model.js';
import eShopReport from'../dist/eshop-report.js';
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
 r=>delete r.report_version,r=>r.report_version='3.0',r=>r.review_evidence=null,
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
