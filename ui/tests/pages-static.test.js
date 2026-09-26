import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';

const root=new URL('../dist/',import.meta.url);
test('Pages entrypoint uses relative static assets and contains a static public-demo landing',async()=>{
 const html=await readFile(new URL('index.html',root),'utf8');
 for(const asset of ['styles.css','pages.css','app.js'])assert.match(html,new RegExp(`(?:href|src)="${asset}"`));
 assert.match(html,/View on GitHub/);assert.match(html,/Explore Demo/);assert.match(html,/continuity explorer/);
 assert.match(html,/<section id="local-landing"[^>]*hidden>/);assert.match(html,/id="hosted-landing"/);
 assert.doesNotMatch(html,/Open Analysis Report|Export Analysis Report|Reset to Demo/);
 assert.doesNotMatch(html,/https?:\/\/[^\"]+(?:analytics|telemetry)/i);
});
