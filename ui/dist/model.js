export const signalNames={change_ownership:'Change ownership',recency:'Recency',change_frequency:'Change frequency',code_area_breadth:'Code-area breadth',unique_contribution:'Unique contribution',historical_persistence:'Historical persistence'};
export const riskOf=x=>x>=.8?'CRITICAL':x>=.6?'HIGH':x>=.4?'MEDIUM':'LOW';
const finite=(v,min=0,max=1)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
export function validateReport(r){
 const fail=()=>{throw Error('Select a valid continuity analyze JSON report. Person and departure exports are not supported here.');};
 if(!r||r.model!=='experimental-v0.1'||!Array.isArray(r.components)||typeof r.revision!=='string'||typeof r.as_of!=='string'||!Number.isFinite(Date.parse(r.as_of))||!Number.isInteger(r.commit_count)||r.commit_count<0)fail();
 if(r.filters!==undefined&&(!r.filters||typeof r.filters!=='object'||['paths','authors'].some(k=>r.filters[k]!==undefined&&(!Array.isArray(r.filters[k])||r.filters[k].some(v=>typeof v!=='string')))))fail();
 if(r.filter_evidence!==undefined&&(!r.filter_evidence||!Number.isInteger(r.filter_evidence.excluded_file_changes)||!Number.isInteger(r.filter_evidence.input_file_changes)))fail();
 const names=new Set();
 for(const c of r.components){
  if(!c||typeof c.component!=='string'||names.has(c.component)||!finite(c.concentration)||c.risk!==riskOf(c.concentration)||!Array.isArray(c.contributors)||!c.contributors.length)fail();
  names.add(c.component);const people=new Set();let shares=0;
  for(const p of c.contributors){
   if(!p||typeof p.contributor!=='string'||!p.contributor||people.has(p.contributor)||typeof p.name!=='string'||!finite(p.share)||!finite(p.score)||!Number.isInteger(p.commits)||p.commits<0||!Array.isArray(p.files)||!p.files.length||p.files.some(f=>typeof f!=='string')||new Set(p.files).size!==p.files.length||!p.signals||Object.keys(signalNames).some(s=>!finite(p.signals[s])))fail();
   people.add(p.contributor);shares+=p.share;
  }
  if(Math.abs(shares-1)>1e-6||Math.abs(c.contributors.reduce((s,p)=>s+p.share*p.share,0)-c.concentration)>1e-6)fail();
 }
 return r;
}
export function departure(report,who){
 return report.components.flatMap(c=>{
  const p=c.contributors.find(p=>p.contributor===who);if(!p)return[];
  const files=new Set(p.files);
  const others=c.contributors.filter(x=>x!==p).map(x=>({...x,overlap:x.files.filter(f=>files.has(f)).length/files.size})).sort((a,b)=>b.overlap-a.overlap||b.score-a.score||(a.contributor<b.contributor?-1:1));
  const covered=new Set(others.flatMap(x=>x.files));
  return[{component:c.component,loss:p.share,remaining:others,successor:others[0]?.overlap>0?others[0]:null,uncovered:p.files.filter(f=>!covered.has(f))}];
 }).sort((a,b)=>b.loss-a.loss||(a.component<b.component?-1:1));
}
export function contributorEvidenceSlices(report){
 const totals=new Map();
 for(const component of report.components)for(const person of component.contributors){
  const current=totals.get(person.contributor)||{id:person.contributor,name:person.name,score:0};
  current.score+=person.score;totals.set(person.contributor,current);
 }
 const ordered=[...totals.values()].sort((left,right)=>right.score-left.score||left.id.localeCompare(right.id));
 const total=ordered.reduce((sum,person)=>sum+person.score,0)||1;
 const slices=ordered.slice(0,5).map(person=>({id:person.id,name:person.name,share:person.score/total}));
 const others=ordered.slice(5).reduce((sum,person)=>sum+person.score,0);
 if(others)slices.push({id:'others',name:'Others',share:others/total});
 return slices;
}
export function demoReport(){
 const people=[['Alex Morgan','alex@example.test'],['Jordan Lee','jordan@example.test'],['Casey Patel','casey@example.test'],['Sam Rivera','sam@example.test']];
 const components=[['src/payments',[.92,.08]],['src/identity',[.78,.22]],['src/catalog',[.53,.32,.15]],['src/checkout',[.40,.30,.20,.10]],['src/notifications',[.34,.33,.33]],['tests/integration',[.25,.25,.25,.25]]].map(([component,shares],i)=>{
  const contributors=shares.map((share,j)=>({contributor:people[(i+j)%4][1],name:people[(i+j)%4][0],share,score:share,commits:Math.round(share*100),files:[`${component}/shared.cs`,`${component}/area-${j}.cs`],signals:{change_ownership:share,recency:.86-j*.12,change_frequency:share,code_area_breadth:.5,unique_contribution:.25,historical_persistence:.8-j*.1}}));
  const concentration=shares.reduce((s,x)=>s+x*x,0);return{component,concentration,risk:riskOf(concentration),contributors};
 });
 return{model:'experimental-v0.1',revision:'synthetic-demo',as_of:'2026-09-01T00:00:00+00:00',commit_count:240,shallow:false,components,configuration:{component_depth:2},filters:{exclude_bots:false,exclude_generated:false}};
}
