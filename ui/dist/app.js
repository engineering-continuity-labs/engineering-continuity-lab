import{validateReport,departure,demoReport,signalNames}from'./model.js';
const $=id=>document.getElementById(id),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(x*100).toLocaleString('tr-TR',{maximumFractionDigits:1})+'%',num=x=>x.toLocaleString('tr-TR');
const colors=['#295ecc','#65a4ce','#e4b85d','#8b83bc','#66a89a'];
let report=demoReport(),selected=report.components[0].component,activePerson=null,view='overview';
const badge=r=>`<span class="badge ${r}">${r}</span>`;
function render(){
 const people=new Set(report.components.flatMap(c=>c.contributors.map(p=>p.contributor)));
 $('revision').textContent='REV '+report.revision.slice(0,12);$('reference').textContent=new Date(report.as_of).toLocaleDateString('tr-TR')+' · referans tarihi';
 const metrics=[['Bileşen',report.components.length,'Dizin tabanlı kapsam'],['Katkı sahibi',people.size,'Dosya değişikliği kanıtı olan'],['Kritik bileşen',report.components.filter(c=>c.risk==='CRITICAL').length,'Yoğunlaşma ≥ 0,80'],['Commit',report.commit_count,'Orijinal Git geçmişi']];
 $('metrics').innerHTML=metrics.map(([label,value,note],i)=>`<article class="metric ${i===2?'critical':''}"><div class="label">${label}</div><div class="value">${num(value)}</div><div class="note">${note}</div></article>`).join('');
 const authors=[...new Map(report.components.flatMap(c=>c.contributors.map(p=>[p.contributor,p.name]))).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
 const previous=$('person').value;$('person').innerHTML=authors.map(([id,name])=>`<option value="${esc(id)}">${esc(name)} · ${esc(id)}</option>`).join('');if(people.has(previous))$('person').value=previous;
 const f=report.filters||{},e=report.filter_evidence;
 $('scope').textContent=`Kapsam: ${report.components.length} bileşen. Sığ klon: ${report.shallow?'evet — geçmiş eksik':'hayır'}. Bot filtresi: ${f.exclude_bots?'açık':'kapalı'}. Üretilmiş dosya filtresi: ${f.exclude_generated?'açık':'kapalı'}. `+(e?`Dışlanan dosya değişikliği: ${e.excluded_file_changes} / ${e.input_file_changes}. `:'')+`Dosya desenleri: ${(f.paths||[]).join(', ')||'yok'}. Yazar desenleri: ${(f.authors||[]).join(', ')||'yok'}.`;
 renderComponents();renderDeparture();
}
function renderComponents(){
 const query=$('search').value.toLocaleLowerCase('tr');const risk=$('risk').value;
 const components=report.components.filter(c=>(!risk||c.risk===risk)&&c.component.toLocaleLowerCase('tr').includes(query)).sort((a,b)=>b.concentration-a.concentration||a.component.localeCompare(b.component));
 if(!components.some(c=>c.component===selected)){selected=components[0]?.component;activePerson=null;}
 $('visible-count').textContent=components.length+' / '+report.components.length;$('empty').hidden=!!components.length;
 $('component-rows').innerHTML=components.map(c=>`<tr class="${selected===c.component?'selected':''}"><td><button class="component-link" data-component="${esc(c.component)}" aria-pressed="${selected===c.component}">${esc(c.component)}</button></td><td>${badge(c.risk)}</td><td>${c.concentration.toFixed(3)}<div class="bar"><span style="width:${c.concentration*100}%"></span></div></td><td>${c.contributors.length}</td></tr>`).join('');
 renderDetail();
}
function renderDetail(){
 const c=report.components.find(c=>c.component===selected);if(!c){$('detail').innerHTML='<h2>Bileşen seçimi</h2><p class="muted">Bu görünümde gösterilecek bileşen yok.</p>';return;}
 const contributors=[...c.contributors].sort((a,b)=>b.share-a.share);const p=contributors.find(p=>p.contributor===activePerson)||contributors[0];activePerson=p.contributor;
 $('detail').innerHTML=`<div class="detail-top"><p class="eyebrow">BİLEŞEN DETAYI</p>${badge(c.risk)}</div><h2>${esc(c.component)}</h2><p class="muted">${contributors.length} kişi · ${new Set(contributors.flatMap(p=>p.files)).size} tarihsel dosya</p><h3>Katkı payları</h3><div class="distribution" aria-label="Katkı payı dağılımı">${contributors.map((p,i)=>`<span style="width:${p.share*100}%;background:${colors[i%colors.length]}"></span>`).join('')}</div>${contributors.map((p,i)=>`<div class="contributor"><button data-contributor="${esc(p.contributor)}" aria-pressed="${p.contributor===activePerson}"><span class="swatch" style="background:${colors[i%colors.length]}"></span>${esc(p.name)}<small>${esc(p.contributor)}</small></button><strong>${pct(p.share)}</strong></div>`).join('')}<div class="signals"><h3>${esc(p.name)} · skorun dayanakları</h3><p class="muted">Ham skor ${p.score.toFixed(3)} · ${p.commits} commit · ${p.files.length} dosya</p>${Object.entries(signalNames).map(([key,name])=>`<div class="signal"><span>${name}</span><div class="bar"><span style="width:${p.signals[key]*100}%"></span></div><span>${p.signals[key].toFixed(2)}</span></div>`).join('')}</div><details class="evidence"><summary>Dosya kanıtları (${p.files.length})</summary><ul>${p.files.map(f=>`<li>${esc(f)}</li>`).join('')}</ul></details>`;
}
function renderDeparture(){
 const impacts=departure(report,$('person').value);
 $('impact-summary').textContent=impacts.length?`${impacts.length} etkilenen bileşen · ${impacts.filter(i=>!i.successor).length} bileşende dosya örtüşmesi olan halef yok`:'Simülasyon için katkı sahibi bulunamadı.';
 $('impact-rows').innerHTML=impacts.map(i=>`<tr><td>${esc(i.component)}</td><td><strong>${pct(i.loss)}</strong><div class="bar"><span style="width:${i.loss*100}%"></span></div></td><td>${i.successor?esc(i.successor.name):'Kanıtlanan aday yok'}</td><td>${i.successor?pct(i.successor.overlap):'—'}</td><td><details><summary>${i.remaining.length} kişi · ${i.uncovered.length} dosya</summary><p>${i.remaining.map(p=>esc(p.name)+' ('+esc(p.contributor)+')').join('<br>')||'Kalan katkı sahibi yok.'}</p><p>${i.uncovered.map(esc).join('<br>')||'Sahipsiz tarihsel dosya yok.'}</p></details></td></tr>`).join('');
}
function setView(next){view=next;for(const name of ['overview','departure']){$(name).hidden=name!==next;$(name+'-tab').classList.toggle('active',name===next);$(name+'-tab').setAttribute('aria-pressed',String(name===next));}}
$('overview-tab').onclick=()=>setView('overview');$('departure-tab').onclick=()=>setView('departure');
$('search').oninput=renderComponents;$('risk').onchange=renderComponents;$('person').onchange=renderDeparture;
$('component-rows').onclick=e=>{const button=e.target.closest('[data-component]');if(button){selected=button.dataset.component;activePerson=null;renderComponents();}};
$('detail').onclick=e=>{const button=e.target.closest('[data-contributor]');if(button){activePerson=button.dataset.contributor;renderDetail();}};
function load(data,name,demo=false){report=validateReport(data);selected=report.components[0]?.component;activePerson=null;$('search').value='';$('risk').value='';$('source-name').textContent=name;$('source-type').textContent=demo?'SENTETİK VERİ':'YEREL JSON';$('message').textContent=report.shallow?'Bu rapor sığ klondan üretilmiş; eksik geçmiş riskleri etkileyebilir.':'';render();}
$('demo').onclick=()=>load(demoReport(),'Örnek rapor',true);
$('upload').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>30*1024*1024)throw Error('Dosya 30 MB sınırını aşıyor. Daha küçük bir rapor seçin.');load(JSON.parse(await file.text()),file.name);}catch(error){$('message').textContent=error instanceof SyntaxError?'JSON okunamadı. Dosyanın geçerli JSON içerdiğini kontrol edin.':error.message;}finally{e.target.value='';}};
render();
// Optional imperative tools share the exact visible application state.
if(document.modelContext?.registerTool){
 const lifecycle=new AbortController();
 addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
 for(const tool of [{name:'show_departure_scenario',description:'Select a contributor in the loaded report and show their departure scenario.',inputSchema:{type:'object',properties:{contributor:{type:'string'}},required:['contributor'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute(input){if(!input||typeof input.contributor!=='string'||!report.components.some(c=>c.contributors.some(p=>p.contributor===input.contributor)))throw Error('Unknown contributor');$('person').value=input.contributor;setView('departure');renderDeparture();return{contributor:input.contributor,impacts:departure(report,input.contributor).map(i=>({component:i.component,loss:i.loss,successor:i.successor?.contributor||null}))};}}]){
  try{Promise.resolve(document.modelContext.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}
 }
}
