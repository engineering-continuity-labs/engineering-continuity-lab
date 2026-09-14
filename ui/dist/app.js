import{validateReport,departure,demoReport,signalNames}from'./model.js';
const $=id=>document.getElementById(id),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(x*100).toLocaleString('en-US',{maximumFractionDigits:1})+'%',num=x=>x.toLocaleString('en-US');
const colors=['#295ecc','#65a4ce','#e4b85d','#8b83bc','#66a89a'];
let report=demoReport(),selected=report.components[0].component,activePerson=null,view='overview';
const badge=r=>`<span class="badge ${r}">${r}</span>`;
function render(){
 const people=new Set(report.components.flatMap(c=>c.contributors.map(p=>p.contributor)));
 $('revision').textContent='REV '+report.revision.slice(0,12);$('reference').textContent=new Date(report.as_of).toLocaleDateString('en-US')+' · reference date';
 const metrics=[['Components',report.components.length,'Directory-based scope'],['Contributors',people.size,'With changed-file evidence'],['Critical components',report.components.filter(c=>c.risk==='CRITICAL').length,'Concentration ≥ 0.80'],['Commits',report.commit_count,'Original Git history']];
 $('metrics').innerHTML=metrics.map(([label,value,note],i)=>`<article class="metric ${i===2?'critical':''}"><div class="label">${label}</div><div class="value">${num(value)}</div><div class="note">${note}</div></article>`).join('');
 const authors=[...new Map(report.components.flatMap(c=>c.contributors.map(p=>[p.contributor,p.name]))).entries()].sort((a,b)=>a[1].localeCompare(b[1],'en'));
 const previous=$('person').value;$('person').innerHTML=authors.map(([id,name])=>`<option value="${esc(id)}">${esc(name)} · ${esc(id)}</option>`).join('');if(people.has(previous))$('person').value=previous;
 const f=report.filters||{},e=report.filter_evidence;
 $('scope').textContent=`Scope: ${report.components.length} components. Shallow clone: ${report.shallow?'yes — history is incomplete':'no'}. Bot filter: ${f.exclude_bots?'enabled':'disabled'}. Generated-file filter: ${f.exclude_generated?'enabled':'disabled'}. `+(e?`Excluded file changes: ${e.excluded_file_changes} / ${e.input_file_changes}. `:'')+`Path patterns: ${(f.paths||[]).join(', ')||'none'}. Author patterns: ${(f.authors||[]).join(', ')||'none'}.`;
 renderComponents();renderDeparture();
}
function renderComponents(){
 const query=$('search').value.toLocaleLowerCase('en');const risk=$('risk').value;
 const components=report.components.filter(c=>(!risk||c.risk===risk)&&c.component.toLocaleLowerCase('en').includes(query)).sort((a,b)=>b.concentration-a.concentration||a.component.localeCompare(b.component,'en'));
 if(!components.some(c=>c.component===selected)){selected=components[0]?.component;activePerson=null;}
 $('visible-count').textContent=components.length+' / '+report.components.length;$('empty').hidden=!!components.length;
 $('component-rows').innerHTML=components.map(c=>`<tr class="${selected===c.component?'selected':''}"><td><button class="component-link" data-component="${esc(c.component)}" aria-pressed="${selected===c.component}">${esc(c.component)}</button></td><td>${badge(c.risk)}</td><td>${c.concentration.toFixed(3)}<div class="bar"><span style="width:${c.concentration*100}%"></span></div></td><td>${c.contributors.length}</td></tr>`).join('');
 renderDetail();
}
function renderDetail(){
 const c=report.components.find(c=>c.component===selected);if(!c){$('detail').innerHTML='<h2>Component selection</h2><p class="muted">There are no components to display in this view.</p>';return;}
 const contributors=[...c.contributors].sort((a,b)=>b.share-a.share);const p=contributors.find(p=>p.contributor===activePerson)||contributors[0];activePerson=p.contributor;
 $('detail').innerHTML=`<div class="detail-top"><p class="eyebrow">COMPONENT DETAIL</p>${badge(c.risk)}</div><h2>${esc(c.component)}</h2><p class="muted">${contributors.length} people · ${new Set(contributors.flatMap(p=>p.files)).size} historical files</p><h3>Contribution shares</h3><div class="distribution" aria-label="Contribution share distribution">${contributors.map((p,i)=>`<span style="width:${p.share*100}%;background:${colors[i%colors.length]}"></span>`).join('')}</div>${contributors.map((p,i)=>`<div class="contributor"><button data-contributor="${esc(p.contributor)}" aria-pressed="${p.contributor===activePerson}"><span class="swatch" style="background:${colors[i%colors.length]}"></span>${esc(p.name)}<small>${esc(p.contributor)}</small></button><strong>${pct(p.share)}</strong></div>`).join('')}<div class="signals"><h3>${esc(p.name)} · score evidence</h3><p class="muted">Raw score ${p.score.toFixed(3)} · ${p.commits} commits · ${p.files.length} files</p>${Object.entries(signalNames).map(([key,name])=>`<div class="signal"><span>${name}</span><div class="bar"><span style="width:${p.signals[key]*100}%"></span></div><span>${p.signals[key].toFixed(2)}</span></div>`).join('')}</div><details class="evidence"><summary>File evidence (${p.files.length})</summary><ul>${p.files.map(f=>`<li>${esc(f)}</li>`).join('')}</ul></details>`;
}
function renderDeparture(){
 const impacts=departure(report,$('person').value);
 $('impact-summary').textContent=impacts.length?`${impacts.length} affected components · ${impacts.filter(i=>!i.successor).length} components have no successor with evidenced file overlap`:'No contributor is available for simulation.';
 $('impact-rows').innerHTML=impacts.map(i=>`<tr><td>${esc(i.component)}</td><td><strong>${pct(i.loss)}</strong><div class="bar"><span style="width:${i.loss*100}%"></span></div></td><td>${i.successor?esc(i.successor.name):'No evidenced candidate'}</td><td>${i.successor?pct(i.successor.overlap):'—'}</td><td><details><summary>${i.remaining.length} people · ${i.uncovered.length} files</summary><p>${i.remaining.map(p=>esc(p.name)+' ('+esc(p.contributor)+')').join('<br>')||'No remaining contributors.'}</p><p>${i.uncovered.map(esc).join('<br>')||'No uncovered historical files.'}</p></details></td></tr>`).join('');
}
function setView(next){view=next;for(const name of ['overview','departure']){$(name).hidden=name!==next;$(name+'-tab').classList.toggle('active',name===next);$(name+'-tab').setAttribute('aria-pressed',String(name===next));}}
$('overview-tab').onclick=()=>setView('overview');$('departure-tab').onclick=()=>setView('departure');
$('search').oninput=renderComponents;$('risk').onchange=renderComponents;$('person').onchange=renderDeparture;
$('component-rows').onclick=e=>{const button=e.target.closest('[data-component]');if(button){selected=button.dataset.component;activePerson=null;renderComponents();}};
$('detail').onclick=e=>{const button=e.target.closest('[data-contributor]');if(button){activePerson=button.dataset.contributor;renderDetail();}};
function load(data,name,demo=false){report=validateReport(data);selected=report.components[0]?.component;activePerson=null;$('search').value='';$('risk').value='';$('source-name').textContent=name;$('source-type').textContent=demo?'SYNTHETIC DATA':'LOCAL JSON';$('message').textContent=report.shallow?'This report was created from a shallow clone; incomplete history can affect the results.':'';render();}
$('demo').onclick=()=>load(demoReport(),'Example report',true);
$('upload').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>30*1024*1024)throw Error('The file exceeds the 30 MB limit. Select a smaller report.');load(JSON.parse(await file.text()),file.name);}catch(error){$('message').textContent=error instanceof SyntaxError?'The JSON could not be read. Confirm that the file contains valid JSON.':error.message;}finally{e.target.value='';}};
render();
