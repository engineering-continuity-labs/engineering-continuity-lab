import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import {renderTraceability,filteredPaths,traceComponents} from '../dist/traceability.js';
import sample from '../dist/traceability-sample.js';
import {validateReport,exportReport,importReport,demoReport} from '../dist/model.js';
const python=process.platform==='win32'?'python':'.venv/bin/python';
const root=new URL('../../',import.meta.url);
const variants=JSON.parse(execFileSync(python,['-c',`import sys,json;sys.path[:0]=['src','tests'];from traceability_report_fixture import synthetic_v3_report;from azure_rest_fixture import profile,IDENTITIES,STAMP,RestFixture;from continuity.traceability_providers.azure_devops import AzureDevOpsTraceabilityProvider;from continuity.analysis.traceability import derive;from continuity.reporting.traceability import with_traceability;r={v:synthetic_v3_report(v) for v in ['BASE','PARTIAL','FAILED','EMPTY','CAPABILITY','PR_PATH_ONLY']};git={k:v for k,v in r['BASE'].items() if k!='traceability_evidence'};r['AZURE']=with_traceability(git,derive(AzureDevOpsTraceabilityProvider(profile(),IDENTITIES,STAMP,'synthetic-snapshot',RestFixture()).acquire()));from dataclasses import replace;from continuity.traceability_providers.synthetic import base_fixture;from continuity.domain.models import DirectoryComponents;e=base_fixture();refs={c:replace(c,identifier=c.identifier[0]*64,algorithm='sha256') for c in e.commits};refs.update({p:replace(p,context=p.context[0]*64,algorithm='sha256') for p in e.changed_paths});e=replace(e,component_configuration='depth-1',commits=tuple(refs[c] for c in e.commits),changed_paths=tuple(refs[p] for p in e.changed_paths),links=tuple(replace(l,source=refs.get(l.source,l.source),target=refs.get(l.target,l.target)) for l in e.links),lookups=tuple(replace(l,endpoint=refs.get(l.endpoint,l.endpoint)) if l.endpoint else l for l in e.lookups));r['SHA256']=with_traceability(git,derive(e,DirectoryComponents(1)));print(json.dumps(r))`],{cwd:root,encoding:'utf8',maxBuffer:16*1024*1024}));

test('sample is actual derived BASE and truthful typed paths/supports/counts render',()=>{
 assert.deepEqual(validateReport(sample),variants.BASE);
 const section=sample.traceability_evidence,html=renderTraceability(section);
 for(const text of ['Collection','COMPLETE','Trace summary','3 / 4','2 / 3','Source boundaries','WORK_ITEM','PULL_REQUEST','COMMIT','CHANGED_PATH','COMPONENT','DIRECT_PROVIDER_LINK','DIRECT_SOURCE_LINK','DERIVED_LINK','synthetic-base','UNRESOLVED_NORMATIVE_SEGMENT','OUTBOUND','INBOUND','SUPPORTED','depth-2','sha1'])assert.ok(html.includes(text),text);
 assert.match(html,/not business correctness/);
 const alternate=validateReport(variants.SHA256),alternateHTML=renderTraceability(alternate.traceability_evidence);assert.match(alternateHTML,/depth-1/);assert.match(alternateHTML,/algorithm sha256/);assert.deepEqual(importReport(exportReport(alternate)),alternate);
 assert.doesNotMatch(html,/<a\b|href=/);
});
test('variants preserve status/null coverage/short paths and absence is unavailable',()=>{
 for(const [name,report] of Object.entries(variants)){
  const section=validateReport(report).traceability_evidence,before=JSON.stringify(section),html=renderTraceability(section);
  assert.ok(html.includes(section.collection.status),name);
  for(const m of section.result.metrics){assert.ok(html.includes(`${m.numerator} / ${m.denominator}`));if(m.value===null)assert.ok(html.includes('Unavailable'));}
  assert.equal(JSON.stringify(section),before);
 }
 assert.match(renderTraceability(),/Traceability unavailable/);
 assert.match(renderTraceability(variants.EMPTY.traceability_evidence),/No paths match/);
 const shorter=variants.PR_PATH_ONLY.traceability_evidence.result.paths.find(p=>p.nodes.some(n=>n.kind==='PR_PATH'));
 assert.ok(shorter);assert.ok(!shorter.nodes.some(n=>n.kind==='COMMIT'));
 assert.match(renderTraceability(variants.AZURE.traceability_evidence),/DIRECT_PROVIDER_LINK/);
});
test('component/status/search filtering changes path display only, with immutable full totals',()=>{
 const section=sample.traceability_evidence,before=JSON.stringify(section);
 assert.ok(traceComponents(section).includes('src/payments'));
 const paths=filteredPaths(section,{component:'src/payments',status:'VERIFIED',query:'1001'});
 assert.ok(paths.length);assert.ok(paths.every(p=>p.status==='VERIFIED'&&p.nodes.some(n=>n.identifier==='src/payments')&&p.nodes.some(n=>n.identifier==='1001')));
 const html=renderTraceability(section,{query:'not-a-real-artifact'});
 assert.match(html,/Paths · 0 of/);assert.match(html,/3 \/ 4/);assert.match(html,/No paths match/);
 assert.equal(JSON.stringify(section),before);
});
test('dynamic text is escaped and static controls/assets retain accessibility hooks',async()=>{
 const section=structuredClone(sample.traceability_evidence);
 section.collection.boundaries[0].snapshot='<img src=x onerror="alert(1)">';
 section.result.paths[0].nodes[0].identifier='<script>alert(1)</script>';
 const html=renderTraceability(section);
 assert.doesNotMatch(html,/<script|<img/);assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);
 const page=await readFile(new URL('../dist/index.html',import.meta.url),'utf8');
 for(const id of ['traceability-tab','trace-demo','trace-component','trace-state','trace-search','trace-content'])assert.ok(page.includes(`id="${id}"`));
 assert.match(page,/<label>Path component/);assert.match(page,/<label>Path status/);assert.match(page,/<label>Artifact search/);
 assert.match(page,/aria-live="polite"/);
});
test('actual app sample/tab/filter/upload/export handlers preserve evidence and reset state',async()=>{
 const elements=new Map(),element=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,classList:{toggle(){}},setAttribute(){},click(){}});return elements.get(id);};
 const oldDocument=globalThis.document,oldLocation=globalThis.location,oldURL=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;let blob;
 globalThis.document={getElementById:element,querySelectorAll:()=>[],createElement:()=>({click(){}})};globalThis.location={hostname:'engineering-continuity-labs.github.io'};URL.createObjectURL=value=>{blob=value;return'blob:test';};URL.revokeObjectURL=()=>{};
 try{
  await import('../dist/app.js');assert.match(element('trace-content').innerHTML,/Traceability unavailable/);
  element('trace-demo').onclick();assert.equal(element('traceability').hidden,false);assert.match(element('trace-content').innerHTML,/3 \/ 4/);
  element('trace-component').value='src/payments';element('trace-component').onchange();element('trace-state').value='VERIFIED';element('trace-state').onchange();element('trace-search').value='missing-artifact';element('trace-search').oninput();assert.match(element('trace-content').innerHTML,/Paths · 0 of/);
  element('export').onclick();const saved=await blob.text();assert.deepEqual(importReport(saved).traceability_evidence,sample.traceability_evidence);
  await element('upload').onchange({target:{files:[{size:saved.length,name:'trace.json',text:async()=>saved}],value:'trace.json'}});
  for(const id of ['trace-component','trace-state','trace-search'])assert.equal(element(id).value,'');assert.doesNotMatch(element('trace-content').innerHTML,/Paths · 0 of/);
  const before=element('trace-content').innerHTML;const bad='{"PRIVATE_SECRET_SENTINEL":';await element('upload').onchange({target:{files:[{size:bad.length,name:'bad.json',text:async()=>bad}],value:'bad.json'}});assert.equal(element('trace-content').innerHTML,before);assert.ok(!element('message').textContent.includes('PRIVATE_SECRET_SENTINEL'));
  const legacy=exportReport(demoReport());await element('upload').onchange({target:{files:[{size:legacy.length,name:'legacy.json',text:async()=>legacy}],value:'legacy.json'}});assert.match(element('trace-content').innerHTML,/Traceability unavailable/);
 }finally{globalThis.document=oldDocument;globalThis.location=oldLocation;URL.createObjectURL=oldURL;URL.revokeObjectURL=oldRevoke;}
});
