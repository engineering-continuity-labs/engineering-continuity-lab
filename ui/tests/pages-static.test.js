import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';

const root=new URL('../dist/',import.meta.url);
test('Pages entrypoint uses relative static assets and contains public-demo actions',async()=>{
 const html=await readFile(new URL('index.html',root),'utf8');
 const app=await readFile(new URL('app.js',root),'utf8');
 for(const asset of ['styles.css','pages.css','app.js'])assert.match(html,new RegExp(`(?:href|src)="${asset}"`));
 assert.match(html,/View on GitHub/);assert.match(html,/Reset to eShop Sample/);assert.match(html,/dotnet\/eShop · validation sample/);assert.match(html,/Open saved JSON report…/);assert.match(html,/Jump to eShop sample/);assert.match(html,/continuity analyze/);assert.doesNotMatch(html,/Explore Demo|Open Analysis Report/);assert.match(html,/Export Analysis Report/);assert.match(html,/Analyze Your Repository/);assert.match(html,/Your report stays in your browser/);
 assert.match(html,/<section id="local-explorer"[^>]*hidden>/);
 assert.match(app,/import eShopReport from '.\/eshop-report\.js'/);assert.doesNotMatch(app,/github\.com\/dotnet\/eShop/);
 assert.ok(html.indexOf('id="local-explorer"')<html.indexOf('aria-label="Report source"'));
 assert.doesNotMatch(html,/https?:\/\/[^\"]+(?:analytics|telemetry)/i);
});
