import{test}from'node:test';
import assert from'node:assert/strict';
import{validateReport,demoReport,departure}from'../dist/model.js';
test('demo validates; concentration and shares agree',()=>assert.equal(validateReport(demoReport()).components.length,6));
test('departure matches file overlap and pre-departure shares',()=>{const r=demoReport(),p=r.components[0].contributors[0];const impact=departure(r,p.contributor).find(i=>i.component==='src/payments');assert.equal(impact.loss,.92);assert.equal(impact.successor.overlap,.5);assert.equal(impact.uncovered.length,1);});
test('rejects person output and corrupt report without changing input',()=>{for(const r of [{components:[{component:'a',share:1}]},null,{...demoReport(),as_of:'bad'}])assert.throws(()=>validateReport(r));const r=demoReport();r.components[0].contributors[0].share=2;assert.throws(()=>validateReport(r));});
test('empty report is valid and has no departure candidates',()=>{const r={...demoReport(),components:[]};validateReport(r);assert.deepEqual(departure(r,'missing'),[]);});
test('no successor without overlapping file evidence',()=>{const r=demoReport();r.components[0].contributors[1].files=['different'];assert.equal(departure(r,r.components[0].contributors[0].contributor).find(i=>i.component==='src/payments').successor,null);});
