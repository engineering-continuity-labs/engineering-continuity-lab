import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import showcase from '../dist/showcase.js';
import {validateReport,importReport,exportReport,demoReport} from '../dist/model.js';
import {reviewSummary,renderSystemOverview,renderRequirements,renderObservations,renderReviewInspector} from '../dist/experience.js';
test('source-derived showcase validates with exact review and qualified observation oracles',()=>{
 const r=validateReport(showcase.report),payments=r.review_evidence.components.find(c=>c.component==='src/payments');
 assert.equal(payments.coverage,.75);assert.equal(payments.risk,'MEDIUM');assert.equal(payments.concentration,5/9);assert.deepEqual(payments.reviewer_units,{'reviewer-alpha':2,'reviewer-beta':1});assert.deepEqual(payments.unreviewed_pull_requests,['54']);assert.deepEqual(payments.excluded_reasons,{self_review:1,provider_declared_bot:1,commented:2});
 assert.deepEqual(reviewSummary(r.review_evidence),{numerator:4,denominator:6,status:'COMPLETE'});assert.deepEqual(showcase.verification.code_traceability,r.traceability_evidence);assert.deepEqual(importReport(exportReport(r)),r);
});
test('overview uses distinct PR units and selected evidence; unavailable never becomes zero',()=>{
 const html=renderSystemOverview(showcase.report,showcase.verification);assert.match(html,/4 \/ 6/);assert.match(html,/2 \/ 4/);assert.match(html,/unknown/);assert.doesNotMatch(html,/readiness score|100%/);
 const missing=renderSystemOverview(demoReport(),null);assert.match(missing,/Unavailable/);assert.doesNotMatch(missing,/0%/);assert.match(renderRequirements(demoReport(),null),/No requirement evidence/);assert.match(renderObservations(null),/does not mean no tests ran/);
 const empty={...showcase.report.review_evidence,provenance:{...showcase.report.review_evidence.provenance,pull_requests:[]}};assert.equal(reviewSummary(empty).denominator,0);
});
test('stories preserve explicit paths, separate reviews/tests and escape dynamic strings',()=>{
 const story=renderRequirements(showcase.report,showcase.verification),obs=renderObservations(showcase.verification),events=renderReviewInspector(showcase.report.review_evidence);
 for(const t of ['Q1','WORK ITEM 1001','PULL REQUEST 51','src/payments/retry.py','ADR1','T1','PASS','SKIPPED','reviewer-alpha'])assert.ok(story.includes(t),t);
 assert.match(story,/not a new requirement-review link/);assert.match(obs,/exact test version and target/);assert.match(events,/CHANGES_REQUESTED/);assert.match(events,/provider_declared_bot/);assert.match(events,/self_review/);
 const dirty=structuredClone(showcase);dirty.verification.requirements[0].reference.identifier='<script>';dirty.report.review_evidence.provenance.pull_requests[0].author.identifier='<img src=x>';
 assert.doesNotMatch(renderRequirements(dirty.report,dirty.verification)+renderReviewInspector(dirty.report.review_evidence),/<script|<img/);
});
test('primary navigation and responsive/native keyboard structure match accepted PO journey',async()=>{
 const html=await readFile(new URL('../dist/index.html',import.meta.url),'utf8'),css=await readFile(new URL('../dist/pages.css',import.meta.url),'utf8');
 const primary=html.match(/<nav class="tabs"[\s\S]*?<\/nav>/)[0];assert.equal((primary.match(/<button/g)||[]).length,4);
 for(const id of ['overview','continuity','traceability','assurance'])assert.ok(primary.includes(`id="${id}-tab"`));assert.doesNotMatch(primary,/v0\.\d|Contributors|Stress/);assert.doesNotMatch(html,/EXPERIMENTAL · v0\.2/);assert.match(html,/Synthetic Product Demo/);assert.match(html,/Public eShop Validation Sample/);assert.match(html,/No review evidence is present/);
 assert.match(css,/flex-wrap:wrap/);assert.match(css,/overflow-x:auto/);assert.match(css,/:focus-visible/);assert.match(html,/Separate synthetic scenario inspector/);assert.match(html,/tabindex="0"/);
});
test('actual default/navigation/source/upload/export/scenario and keyboard handlers preserve evidence scope',async()=>{
 const nodes=new Map(),element=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,open:false,pressed:{},classList:{toggle(){}},setAttribute(k,v){this.pressed[k]=v;},click(){this.clicked=true;}});return nodes.get(id);};
 const label={};let blob;const oldDocument=globalThis.document,oldLocation=globalThis.location,oldCreate=URL.createObjectURL,oldRevoke=URL.revokeObjectURL;
 globalThis.document={getElementById:element,querySelectorAll:()=>[label],createElement:()=>({click(){}})};globalThis.location={hostname:'engineering-continuity-labs.github.io'};URL.createObjectURL=b=>{blob=b;return'blob:test';};URL.revokeObjectURL=()=>{};
 const upload=async raw=>element('upload').onchange({target:{files:[{size:raw.length,name:'report.json',text:async()=>raw}],value:'report.json'}});
 const before=JSON.stringify(showcase);
 try{await import('../dist/app.js');assert.equal(element('overview').hidden,false);assert.equal(element('continuity').hidden,true);assert.match(element('overview-content').innerHTML,/4 \/ 6/);assert.ok(element('review-rows').innerHTML);assert.match(element('requirements-content').innerHTML,/Q1/);
  element('continuity-tab').onclick();assert.equal(element('components').hidden,false);element('contributors-tab').onclick();assert.equal(element('contributors').hidden,false);assert.equal(element('components').hidden,true);element('assurance-tab').onclick();assert.equal(element('reviews').hidden,false);assert.equal(element('overview-tab').pressed['aria-pressed'],'false');
  const overview=element('overview-content').innerHTML;element('verification-scenario').value='STALE_TARGET';element('verification-scenario').onchange();assert.equal(element('overview-content').innerHTML,overview);
  let prevented=false;label.onkeydown({key:'Enter',preventDefault(){prevented=true;}});assert.equal(prevented,true);assert.equal(element('upload').clicked,true);
  element('export').onclick();const saved=await blob.text();assert.deepEqual(importReport(saved),showcase.report);await upload(saved);assert.match(element('requirements-content').innerHTML,/unavailable/);assert.doesNotMatch(element('overview-content').innerHTML,/2 \/ 4/);
  element('demo').onclick();assert.equal(element('source-type').textContent,'PUBLIC VALIDATION SAMPLE');assert.equal(element('explore-source').textContent,'Explore selected system');assert.match(element('review-summary').textContent,/PARTIAL/);assert.match(element('requirements-content').innerHTML,/unavailable/);
  const legacy=exportReport(demoReport());await upload(legacy);assert.equal(element('explore-source').textContent,'Explore selected system');assert.equal(element('review-rows').innerHTML,'');assert.match(element('review-summary').textContent,/Absence does not mean zero/);const prior=element('overview-content').innerHTML;await upload('{"TOKEN_SENTINEL":');assert.equal(element('overview-content').innerHTML,prior);assert.doesNotMatch(element('message').textContent,/TOKEN_SENTINEL/);
  element('showcase-demo').onclick();assert.equal(element('source-type').textContent,'SYNTHETIC');assert.match(element('requirements-content').innerHTML,/Q1/);assert.equal(JSON.stringify(showcase),before);
 }finally{globalThis.document=oldDocument;globalThis.location=oldLocation;URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;}
});

test('review ordering and full declared metadata remain inspectable at equal timestamps',()=>{
 const pr=showcase.report.review_evidence.provenance.pull_requests.find(p=>p.identifier==='51'),events=pr.reviews.filter(e=>e.reviewer?.identifier==='reviewer-alpha');
 assert.equal(events[0].submitted_at,events[1].submitted_at);assert.equal(events[0].provider_order,0);assert.equal(events[1].provider_order,1);
 const html=renderReviewInspector(showcase.report.review_evidence);
 for(const token of ['provider_order 0','provider_order 1','merged_at','is_bot false','is_bot true','dismissed false','display name','submitted_at','collection_status','component_depth'])assert.ok(html.includes(token),token);
 assert.equal(showcase.report.review_evidence.components.find(c=>c.component==='src/payments').covered_pull_requests,3);
});
