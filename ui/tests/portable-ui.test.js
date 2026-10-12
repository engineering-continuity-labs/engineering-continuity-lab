import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {importReport,exportReport,validateReport} from '../dist/model.js';
import {portablePresentation,sha256} from '../dist/verification-model.js';
import {renderVerification,filterVerification} from '../dist/verification.js';
const venv=new URL('../../.venv/bin/python',import.meta.url),python=process.env.PYTHON??(existsSync(venv)?fileURLToPath(venv):'python3');
const root=new URL('../../',import.meta.url);
const run=script=>JSON.parse(execFileSync(python,['-c',"import sys,json;sys.path[:0]=['src','tests'];from test_portable_evidence import portable;"+script],{cwd:root,encoding:'utf8',maxBuffer:16*1024*1024}));
const scenarios=run("print(json.dumps({v:portable(v)[0] for v in ['BASE','EMPTY','NO_LINKS','PARTIAL','FAILED','UNSUPPORTED','STALE_TARGET','CONFLICTING_RUN','LIMIT']}))");
test('all actual portable scenarios validate/export and retain exact counts/provenance',()=>{
 for(const [name,r] of Object.entries(scenarios)){const validated=importReport(JSON.stringify(r));assert.deepEqual(importReport(exportReport(validated)),r,name);const p=portablePresentation(r.verification_evidence,r.traceability_evidence);const html=renderVerification(p);assert.match(html,/OFFLINE DECLARED/);assert.match(html,/historical declared observation/);assert.equal(p.synthetic,false);}
 assert.ok(scenarios.BASE.verification_evidence.result.metrics.every(m=>m.numerator===2&&m.denominator===4));
 assert.deepEqual(scenarios.BASE.verification_evidence.result.outcomes,{PASS:1,FAIL:1,SKIPPED:1,UNKNOWN:1});
 assert.equal(sha256('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
test('shared forged evidence rejects in Python and browser',()=>{
 const bad=[];const mutate=fn=>{const r=structuredClone(scenarios.BASE);fn(r.verification_evidence,r);bad.push(r);};
 mutate(s=>s.result.outcomes.PASS++);mutate(s=>s.result.metrics[0].numerator++);mutate(s=>s.result.requirements[0].tests='VERIFIED');mutate(s=>s.collection.artifacts.push(s.collection.artifacts[0]));mutate(s=>s.collection.snapshot.fingerprint='0'.repeat(64));mutate(s=>s.collection.runs[0].outcome='FUTURE');mutate(s=>s.collection.runs[0].qualified=true);mutate(s=>s.collection.artifacts[0].description='PRIVATE_SENTINEL');mutate(s=>s.collection.artifacts[0].identifier='TOKEN_SENTINEL');mutate(s=>s.result.paths[0].code_path.supports.reverse());mutate((s,r)=>r.report_version='5.0');mutate((s,r)=>r.extra=true);mutate(s=>s.collection.lookups[0].capability='UNKNOWN');
 for(const r of bad)assert.throws(()=>validateReport(r));
 const script="import sys,json;sys.path[:0]=['src'];from continuity.reporting.portable import report_from_json;items=json.load(sys.stdin);results=[]\nfor item in items:\n try: report_from_json(json.dumps(item));results.append(True)\n except ValueError: results.append(False)\nprint(json.dumps(results))";
 const accepted=JSON.parse(execFileSync(python,['-c',script],{cwd:root,input:JSON.stringify(bad),encoding:'utf8'}));assert.ok(accepted.every(v=>v===false));
});
test('reordered portable sets accept while supporting-hop order remains meaningful',()=>{
 const r=structuredClone(scenarios.BASE);for(const k of ['artifacts','associations','runs','lookups'])r.verification_evidence.collection[k].reverse();for(const k of ['metrics','requirements','paths','runs','gaps','diagnostics','associations'])r.verification_evidence.result[k].reverse();assert.ok(validateReport(r));
 const presentation=portablePresentation(r.verification_evidence,r.traceability_evidence),before=JSON.stringify(presentation.metrics),filtered=filterVerification(presentation,'Q1');assert.ok(filtered.requirements.length<presentation.requirements.length);assert.equal(JSON.stringify(filtered.metrics),before);assert.deepEqual(filtered.outcomes,presentation.outcomes);
});
test('actual loaded v4 app filters and exports; invalid import preserves prior report',async()=>{
 const nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,classList:{toggle(){}},setAttribute(){},click(){}});return nodes.get(id);};
 const oldDocument=globalThis.document,oldLocation=globalThis.location,oldCreate=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;let blob;
 globalThis.document={getElementById:element,querySelectorAll:()=>[],createElement:()=>({click(){}})};globalThis.location={hostname:'engineering-continuity-labs.github.io'};URL.createObjectURL=b=>{blob=b;return 'blob:test';};URL.revokeObjectURL=()=>{};
 const upload=async text=>element('upload').onchange({target:{files:[{size:text.length,name:'evidence.json',text:async()=>text}],value:'evidence.json'}});
 try{await import('../dist/app.js');await upload(JSON.stringify(scenarios.BASE));assert.match(element('portable-verification-content').innerHTML,/OFFLINE DECLARED/);assert.match(element('portable-verification-content').innerHTML,/2 \/ 4/);element('portable-verification-search').value='Q1';element('portable-verification-search').oninput();assert.match(element('portable-verification-content').innerHTML,/2 \/ 4/);element('export').onclick();assert.deepEqual(importReport(await blob.text()),scenarios.BASE);const before=element('portable-verification-content').innerHTML;const bad=structuredClone(scenarios.BASE);bad.verification_evidence.result.outcomes.PASS=99;await upload(JSON.stringify(bad));assert.equal(element('portable-verification-content').innerHTML,before);element('export').onclick();assert.deepEqual(importReport(await blob.text()),scenarios.BASE);}
 finally{globalThis.document=oldDocument;globalThis.location=oldLocation;URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;}
});

test('TOML CLI → actual four-area UI → browser export → Python import and source isolation',async()=>{
 const raw=execFileSync(python,['-m','continuity','evidence-attach','--report','examples/v0.4-traceability-v3.json','--manifest','examples/v0.4-evidence.toml'],{cwd:root,encoding:'utf8',maxBuffer:16*1024*1024});
 const portable=importReport(raw),nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,classList:{toggle(){}},setAttribute(){},click(){}});return nodes.get(id);};
 const previous={document:globalThis.document,location:globalThis.location,create:URL.createObjectURL,revoke:URL.revokeObjectURL};let blob;
 globalThis.document={getElementById:element,querySelectorAll:()=>[],createElement:()=>({click(){}})};globalThis.location={hostname:'engineering-continuity-labs.github.io'};URL.createObjectURL=b=>{blob=b;return 'blob:portable';};URL.revokeObjectURL=()=>{};
 const upload=async text=>element('upload').onchange({target:{files:[{size:Buffer.byteLength(text),name:'my-evidence.json',text:async()=>text}],value:'x'}});
 try{
  await import('../dist/app.js?portable-e2e');await upload(raw);
  assert.match(element('overview-content').innerHTML,/2 \/ 4/);assert.match(element('requirements-content').innerHTML,/Q1/);assert.match(element('requirements-content').innerHTML,/WORK ITEM/);assert.match(element('observation-content').innerHTML,/PASS/);assert.match(element('observation-content').innerHTML,/OFFLINE DECLARED/);assert.doesNotMatch(element('requirements-content').innerHTML,/SYNTHETIC|fictional/);assert.equal(element('source-type').textContent,'LOCAL JSON');
  for(const area of ['overview','continuity','traceability','assurance']){element(area+'-tab').onclick();assert.equal(element(area).hidden,false);}
  const overview=element('overview-content').innerHTML;element('verification-scenario').value='EMPTY';element('verification-scenario').onchange();assert.equal(element('overview-content').innerHTML,overview);
  element('export').onclick();const exported=await blob.text();assert.deepEqual(importReport(exported),portable);
  const reopened=JSON.parse(execFileSync(python,['-c',"import sys;from continuity.reporting.portable import report_from_json,report_to_json;print(report_to_json(report_from_json(sys.stdin.read())))"],{cwd:root,input:exported,encoding:'utf8',maxBuffer:16*1024*1024}));assert.deepEqual(reopened,portable);
  await upload(raw.replace('"report_version":"4.0"','"report_version":"99.0"'));assert.equal(element('overview-content').innerHTML,overview);assert.doesNotMatch(element('message').textContent,/99\.0/);
  await element('upload').onchange({target:{files:[{size:1,name:'bad-utf8.json',arrayBuffer:async()=>new Uint8Array([255]).buffer}],value:'x'}});assert.equal(element('overview-content').innerHTML,overview);assert.equal(element('message').textContent,'Select a valid continuity analyze JSON report. Person and departure exports are not supported here.');
  element('demo').onclick();assert.match(element('requirements-content').innerHTML,/Unavailable/i);assert.match(element('portable-verification-content').innerHTML,/No attached/);
  element('showcase-demo').onclick();assert.equal(element('source-type').textContent,'SYNTHETIC');assert.match(element('overview-content').innerHTML,/2 \/ 4/);
 }finally{globalThis.document=previous.document;globalThis.location=previous.location;URL.createObjectURL=previous.create;URL.revokeObjectURL=previous.revoke;}
});
