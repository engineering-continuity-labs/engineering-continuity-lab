/** Exercise actual app rendering and upload/download handlers without network. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {demoReport,exportReport,importReport} from '../dist/model.js';
import sample from '../dist/eshop-reviews.js';

test('static Reviews render, export and reopen retain the exact rows and provenance',async()=>{
 const elements=new Map();
 const element=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,classList:{toggle(){}},setAttribute(){},click(){}});return elements.get(id);};
 let blob;
 const oldDocument=globalThis.document,oldLocation=globalThis.location,oldURL=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;
 globalThis.document={getElementById:element,querySelectorAll:()=>[],createElement:()=>({click(){}})};
 globalThis.location={hostname:'engineering-continuity-labs.github.io'};
 URL.createObjectURL=value=>{blob=value;return'blob:test';};URL.revokeObjectURL=()=>{};
 try{
  await import('../dist/app.js');
  assert.ok(element('review-rows').innerHTML.includes('PARTIAL'));
  assert.ok(element('review-summary').textContent.includes(sample.provenance.provenance.evidence_boundary));
  assert.ok(element('review-summary').textContent.includes(sample.provenance.provenance.retrieved_at));
  const before=element('review-rows').innerHTML,summary=element('review-summary').textContent;
  element('export').onclick();
  const json=await blob.text(),saved=importReport(json);
  assert.equal(saved.report_version,'2.0');assert.deepEqual(saved.review_evidence,sample);
  await element('upload').onchange({target:{files:[{size:json.length,name:'export.json',text:async()=>json}],value:'export.json'}});
  assert.equal(element('review-rows').innerHTML,before);assert.equal(element('review-summary').textContent,summary);
  assert.match(before,/Unavailable \(component scope differs or is unknown\)/);
  assert.match(before,/provider_declared_bot/);
  // A compatible synthetic report can compare separate component HHIs.
  const compatible={...demoReport(),report_version:'2.0',review_evidence:{
   component_depth:2,provenance:{provenance:{provider:'fixture',repository:'public/example',evidence_boundary:'one merged PR fixture',retrieved_at:'2026-10-07T00:00:00Z'},status:'COMPLETE',diagnostics:[],pull_requests:[{identifier:'1',author:{identifier:'author',display_name:null,is_bot:false},merged_at:'2026-10-07T00:00:00Z',changed_paths:['src/payments/a.py'],reviews:[]}]},
   components:[{component:'src/payments',mapped_pull_requests:1,covered_pull_requests:0,coverage:0,coverage_status:'COMPLETE',reviewer_units:{},reviewer_shares:{},concentration:null,risk:null,unreviewed_pull_requests:['1'],excluded_reasons:{}}]
  }};
  const matching=exportReport(compatible);
  await element('upload').onchange({target:{files:[{size:matching.length,name:'matching.json',text:async()=>matching}],value:'matching.json'}});
  assert.match(element('review-rows').innerHTML,/0\.853/);
  assert.doesNotMatch(element('review-rows').innerHTML,/component scope differs/);
  assert.match(element('review-rows').innerHTML,/Unavailable/); // no qualifying reviewer HHI
  // Absence is rendered unavailable and does not invent a zero-review population.
  const v1=exportReport(demoReport());
  await element('upload').onchange({target:{files:[{size:v1.length,name:'v1.json',text:async()=>v1}],value:'v1.json'}});
  assert.equal(element('review-rows').innerHTML,'');assert.match(element('review-summary').textContent,/Run an analysis/);
  // Malformed input cannot replace the valid report currently rendered.
  const bad=JSON.stringify({...demoReport(),report_version:'2.0',review_evidence:{components:[]}});
  await element('upload').onchange({target:{files:[{size:bad.length,name:'bad.json',text:async()=>bad}],value:'bad.json'}});
  assert.equal(element('review-rows').innerHTML,'');assert.match(element('message').textContent,/valid continuity/);
  const app=await readFile(new URL('../dist/app.js',import.meta.url),'utf8');
  assert.doesNotMatch(app,/api\.github\.com/);
 }finally{globalThis.document=oldDocument;globalThis.location=oldLocation;URL.createObjectURL=oldURL;URL.revokeObjectURL=oldRevoke;}
});
