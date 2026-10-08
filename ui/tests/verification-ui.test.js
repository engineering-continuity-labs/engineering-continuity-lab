import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import scenarios from '../dist/verification-sample.js';
import {renderVerification} from '../dist/verification.js';
import {importReport,demoReport,exportReport} from '../dist/model.js';
const venv=new URL('../../.venv/bin/python',import.meta.url);
const python=process.env.PYTHON??(existsSync(venv)?fileURLToPath(venv):'python3');
test('bundled scenarios are fresh derivations with the exact BASE oracle',()=>{
 execFileSync(python,['scripts/generate_v04_demo.py','--check'],{cwd:new URL('../../',import.meta.url)});
 assert.equal(scenarios.BASE.schema_version,'v0.4-demo-1');
 assert.ok(scenarios.BASE.metrics.every(m=>m.numerator===2&&m.denominator===4));
 assert.deepEqual(scenarios.BASE.outcomes,{PASS:1,FAIL:1,SKIPPED:1,UNKNOWN:1});
 for(const report of Object.values(scenarios)){assert.throws(()=>importReport(JSON.stringify(report)));const before=JSON.stringify(report);assert.match(renderVerification(report),/SYNTHETIC/);assert.equal(JSON.stringify(report),before);}
});
test('renderer preserves qualification, unknown coverage, provenance and escaped values',()=>{
 const base=renderVerification(scenarios.BASE);
 for(const text of ['2 / 4','DIRECT_PROVIDER_LINK','v1','MISSING','fingerprint','no real','depth-2','algorithm sha1','context','provider'])assert.ok(base.includes(text),text);
 assert.match(renderVerification(scenarios.STALE_TARGET),/TARGET_MISMATCH/);
 assert.match(renderVerification(scenarios.CONFLICTING_RUN),/CONFLICT/);
 assert.match(renderVerification(scenarios.EMPTY),/Unavailable/);
 assert.match(renderVerification(scenarios.LIMIT),/LIMIT_EXHAUSTED/);
 const dirty=structuredClone(scenarios.BASE);dirty.warning='<script>alert(1)</script>';dirty.artifacts[0].identifier='<img src=x>';dirty.requirements[0].reference.identifier='<img src=x>';
 const html=renderVerification(dirty);assert.doesNotMatch(html,/<script|<img|href=/);assert.match(html,/&lt;script/);assert.match(html,/&lt;img/);
});
test('actual app switches scenarios and exports isolated demo without replacing Git report',async()=>{
 const nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,classList:{toggle(){}},setAttribute(){},click(){}});return nodes.get(id);};
 const oldDocument=globalThis.document,oldLocation=globalThis.location,oldCreate=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;let blob;
 globalThis.document={getElementById:element,querySelectorAll:()=>[],createElement:()=>({click(){}})};globalThis.location={hostname:'engineering-continuity-labs.github.io'};URL.createObjectURL=b=>{blob=b;return 'blob:test';};URL.revokeObjectURL=()=>{};
 try{
  await import('../dist/app.js');element('verification-demo').onclick();assert.equal(element('verification').hidden,false);assert.match(element('verification-content').innerHTML,/2 \/ 4/);
  element('export').onclick();const original=await blob.text();assert.ok(importReport(original));
  element('verification-scenario').value='STALE_TARGET';element('verification-scenario').onchange();assert.match(element('verification-content').innerHTML,/TARGET_MISMATCH/);
  element('verification-export').onclick();const saved=await blob.text();assert.deepEqual(JSON.parse(saved),scenarios.STALE_TARGET);
  await element('upload').onchange({target:{files:[{size:saved.length,name:'demo.json',text:async()=>saved}],value:'demo.json'}});
  element('export').onclick();assert.equal(await blob.text(),original);
 }finally{globalThis.document=oldDocument;globalThis.location=oldLocation;URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;}
});
test('alternate derived code configuration and hash identities stay visible',()=>{
 const script=`import sys,json;sys.path[:0]=['src'];from dataclasses import replace;from continuity.traceability_providers.synthetic import base_fixture;from continuity.traceability_providers.verification_synthetic import fixture;from continuity.analysis.traceability import derive as code_derive;from continuity.analysis.verification import derive,snapshot_for;from continuity.domain.models import DirectoryComponents;from continuity.reporting.verification import to_dict;e=base_fixture();refs={c:replace(c,identifier=c.identifier[0]*64,algorithm='sha256') for c in e.commits};refs.update({p:replace(p,context=p.context[0]*64,algorithm='sha256') for p in e.changed_paths});e=replace(e,component_configuration='depth-1',commits=tuple(refs[c] for c in e.commits),changed_paths=tuple(refs[p] for p in e.changed_paths),links=tuple(replace(l,source=refs.get(l.source,l.source),target=refs.get(l.target,l.target)) for l in e.links),lookups=tuple(replace(l,endpoint=refs.get(l.endpoint,l.endpoint)) if l.endpoint else l for l in e.lookups));code=code_derive(e,DirectoryComponents(1));v=fixture();snapshot=snapshot_for(code,v.snapshot.alias);v=replace(v,code=code,snapshot=snapshot,runs=tuple(replace(r,target=snapshot) for r in v.runs));print(json.dumps(to_dict(derive(v))))`;
 const report=JSON.parse(execFileSync(python,['-c',script],{cwd:new URL('../../',import.meta.url),encoding:'utf8',maxBuffer:16*1024*1024}));
 const html=renderVerification(report);assert.match(html,/mapping depth-1/);assert.match(html,/algorithm sha256/);assert.match(html,/context/);
});
