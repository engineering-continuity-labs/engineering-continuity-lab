import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';

const root=new URL('../dist/',import.meta.url);
test('Pages entrypoint uses relative static assets and contains public-demo actions',async()=>{
 const html=await readFile(new URL('index.html',root),'utf8');
 for(const asset of ['styles.css','pages.css','app.js'])assert.match(html,new RegExp(`(?:href|src)="${asset}"`));
 assert.match(html,/View on GitHub/);assert.match(html,/Open Analysis Report/);assert.match(html,/Export Analysis Report/);assert.match(html,/Analyze Your Repository/);assert.match(html,/Your report stays in your browser/);
 assert.match(html,/<section id="local-explorer"[^>]*hidden>/);
 assert.ok(html.indexOf('id="local-explorer"')<html.indexOf('aria-label="Report source"'));
 assert.doesNotMatch(html,/https?:\/\/[^\"]+(?:analytics|telemetry)/i);
});
