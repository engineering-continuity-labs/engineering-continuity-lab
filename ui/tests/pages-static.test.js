import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';

const root=new URL('../dist/',import.meta.url);
test('Pages entrypoint uses relative static assets and contains public-demo actions',async()=>{
 const html=await readFile(new URL('index.html',root),'utf8');
 const app=await readFile(new URL('app.js',root),'utf8');
 const pages=await readFile(new URL('pages.css',root),'utf8');
 for(const asset of ['styles.css','pages.css','app.js'])assert.match(html,new RegExp(`(?:href|src)="${asset}"`));
 assert.match(html,/View on GitHub/);assert.match(html,/Public eShop Validation Sample/);assert.match(html,/Atlas Commerce · fictional system/);assert.match(html,/Open saved JSON report…/);assert.match(html,/From engineering evidence to executive clarity\./);assert.match(html,/Explore Atlas Commerce/);assert.match(html,/HOW IT WORKS/);assert.match(html,/Acquire evidence/);assert.match(html,/Normalize evidence/);assert.match(html,/Generate Engineering System Review/);assert.match(html,/Choose your evidence source/);assert.match(html,/SYNTHETIC DEMO PROJECT/);assert.match(html,/Use your engineering evidence/);assert.match(html,/Azure DevOps Server\/on-prem HTTPS Git clone URL/);assert.match(html,/Existing local review/);assert.match(html,/HTTPS Git clone URL/);assert.match(html,/public site does not connect to Azure DevOps or GitHub/);assert.match(html,/continuity analyze/);assert.match(html,/data-tooltip="Choose a saved JSON report/);assert.match(html,/data-tooltip="Download the report currently shown here/);assert.match(html,/aria-describedby="open-report-help"/);assert.match(html,/aria-describedby="export-report-help"/);assert.match(html,/id="open-report-help"/);assert.match(html,/id="export-report-help"/);assert.match(html,/Open a previously generated/);assert.match(html,/tabindex="0"/);assert.match(app,/label\[for="upload"\]/);assert.match(app,/repositoryInputError/);assert.doesNotMatch(app,/review_evidence:true/);assert.doesNotMatch(html,/Explore Demo|Open Analysis Report/);assert.match(html,/Export Analysis Report/);assert.match(html,/Analyze Your Repository/);assert.match(html,/Your report stays in your browser/);assert.doesNotMatch(html,/href="engineering-review\.html" target="_blank"/);
 assert.match(html,/<section id="local-explorer"[^>]*hidden>/);
 assert.match(html,/class="app-shell"/);assert.match(html,/class="app-nav"/);assert.match(html,/Start a Review/);assert.match(html,/Executive Review/);assert.match(html,/Evidence &amp; Methodology/);
 assert.match(pages,/\.app-body\{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif\}/);assert.match(pages,/\.app-content main\{padding:30px 48px 56px\}/);
 assert.match(html,/<button id="overview-tab" class="active" aria-pressed="true">Overview<\/button>/);assert.match(html,/<section id="overview">/);assert.match(html,/<section id="components">/);
 assert.match(app,/import eShopReport from '.\/eshop-report\.js'/);assert.doesNotMatch(app,/github\.com\/dotnet\/eShop/);
 assert.ok(html.indexOf('id="local-explorer"')<html.indexOf('aria-label="Report source"'));
 assert.doesNotMatch(html,/https?:\/\/[^\"]+(?:analytics|telemetry)/i);
});
