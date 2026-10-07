export const signalNames={change_ownership:'Change ownership',recency:'Recency',change_frequency:'Change frequency',code_area_breadth:'Code-area breadth',unique_contribution:'Unique contribution',historical_persistence:'Historical persistence'};
export const riskOf=x=>x>=.8?'CRITICAL':x>=.6?'HIGH':x>=.4?'MEDIUM':'LOW';
const finite=(v,min=0,max=1)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const text=v=>typeof v==='string'&&!!v.trim();
const count=v=>Number.isSafeInteger(v)&&v>=0;
const strings=v=>Array.isArray(v)&&v.every(text)&&new Set(v).size===v.length;
const timestamp=v=>text(v)&&/(Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v));
const statuses=['COMPLETE','PARTIAL','FAILED'];
function qualifyingEvidence(pr){
 const newest=new Map(),missing=[];
 const compare=(a,b)=>(a.submitted_at===null?-Infinity:Date.parse(a.submitted_at))-(b.submitted_at===null?-Infinity:Date.parse(b.submitted_at))||((a.provider_order??-1)-(b.provider_order??-1))||(a.identifier<b.identifier?-1:a.identifier>b.identifier?1:0);
 for(const event of pr.reviews){
  if(event.reviewer===null){missing.push(event);continue;}
  const key=event.reviewer.identifier.toLowerCase(),previous=newest.get(key);
  if(!previous||compare(event,previous)>0)newest.set(key,event);
 }
 const units=[],exclusions={};
 const exclude=reason=>exclusions[reason]=(exclusions[reason]??0)+1;
 for(const [key,event] of newest){
  const reason=event.dismissed||event.state==='DISMISSED'?'dismissed':key===pr.author.identifier.toLowerCase()?'self_review':event.reviewer.is_bot?'provider_declared_bot':event.state==='COMMENTED'?'commented':!['APPROVED','CHANGES_REQUESTED'].includes(event.state)?'unsupported_state':null;
  if(reason)exclude(reason);else units.push(key);
 }
 for(const event of missing)exclude('missing_reviewer');
 return {units,exclusions};
}
function reconcileReviews(review,fail){
 const evidence=new Map(review.provenance.pull_requests.map(pr=>[pr.identifier,{pr,...qualifyingEvidence(pr)}]));
 const globalUnits=new Map();let covered=0;
 for(const {units} of evidence.values()){if(units.length)covered++;for(const id of units)globalUnits.set(id,(globalUnits.get(id)??0)+1);}
 const sameCounts=(a,b)=>Object.keys(a).length===Object.keys(b).length&&Object.entries(a).every(([key,n])=>b[key]===n);
 const sameIds=(a,b)=>a.length===b.length&&a.every(id=>b.includes(id));
 for(const c of review.components){
  if(c.covered_pull_requests>covered||Object.entries(c.reviewer_units).some(([id,n])=>n>(globalUnits.get(id)??0))||c.unreviewed_pull_requests.some(id=>evidence.get(id).units.length))fail();
 }
 if(!Number.isInteger(review.component_depth))return;
 const expected=new Map();
 for(const {pr,units,exclusions} of evidence.values()){
  const components=new Set(pr.changed_paths.map(path=>path.split('/').slice(0,-1).slice(0,review.component_depth).join('/')||'(root)'));
  for(const component of components){
   if(!expected.has(component))expected.set(component,{mapped:0,covered:0,units:Object.create(null),excluded:Object.create(null),unreviewed:[]});
   const c=expected.get(component);c.mapped++;if(units.length)c.covered++;else c.unreviewed.push(pr.identifier);
   for(const id of units)c.units[id]=(c.units[id]??0)+1;
   for(const [reason,n] of Object.entries(exclusions))c.excluded[reason]=(c.excluded[reason]??0)+n;
  }
 }
 if(expected.size!==review.components.length)fail();
 for(const c of review.components){
  const e=expected.get(c.component);
  if(!e||e.mapped!==c.mapped_pull_requests||e.covered!==c.covered_pull_requests||!sameCounts(e.units,c.reviewer_units)||!sameCounts(e.excluded,c.excluded_reasons)||!sameIds(e.unreviewed,c.unreviewed_pull_requests))fail();
 }
}
function validateReviews(review,fail){
 if(!object(review)||!object(review.provenance)||!Array.isArray(review.components))fail();
 if(review.component_depth!==undefined&&review.component_depth!==null&&(!Number.isSafeInteger(review.component_depth)||review.component_depth<1))fail();
 const collection=review.provenance,p=collection.provenance;
 if(!object(p)||!['provider','repository','evidence_boundary'].every(k=>text(p[k]))||!timestamp(p.retrieved_at)||!statuses.includes(collection.status)||!Array.isArray(collection.diagnostics)||collection.diagnostics.some(x=>!text(x))||!Array.isArray(collection.pull_requests))fail();
 // Public references must never encode credentials or query/fragment data.
 if(/[?#]/.test(p.repository)||p.repository.includes('@'))fail();
 for(const k of ['closed_pull_requests_inspected','merged_pull_requests_observed'])if(collection[k]!==undefined&&!count(collection[k]))fail();
 const prIds=new Set();
 const identity=i=>object(i)&&text(i.identifier)&&(i.display_name===null||typeof i.display_name==='string')&&typeof i.is_bot==='boolean';
 for(const pr of collection.pull_requests){
  if(!object(pr)||!text(pr.identifier)||prIds.has(pr.identifier)||!identity(pr.author)||!timestamp(pr.merged_at)||!strings(pr.changed_paths)||!pr.changed_paths.length||!Array.isArray(pr.reviews))fail();
  prIds.add(pr.identifier);const ids=new Set();
  for(const event of pr.reviews){
   if(!object(event)||!text(event.identifier)||ids.has(event.identifier)||!['APPROVED','CHANGES_REQUESTED','COMMENTED','DISMISSED','UNKNOWN'].includes(event.state)||(event.reviewer!==null&&!identity(event.reviewer))||(event.submitted_at!==null&&!timestamp(event.submitted_at))||(event.provider_order!==null&&!count(event.provider_order))||typeof event.dismissed!=='boolean')fail();
   ids.add(event.identifier);
  }
 }
 const names=new Set();
 for(const c of review.components){
  if(!object(c)||!text(c.component)||names.has(c.component)||!count(c.covered_pull_requests)||!count(c.mapped_pull_requests)||c.covered_pull_requests>c.mapped_pull_requests||c.coverage_status!==collection.status||!object(c.reviewer_units)||!strings(c.unreviewed_pull_requests)||c.unreviewed_pull_requests.length!==c.mapped_pull_requests-c.covered_pull_requests||c.unreviewed_pull_requests.some(id=>!prIds.has(id))||!object(c.excluded_reasons)||Object.entries(c.excluded_reasons).some(([k,v])=>!text(k)||!count(v)))fail();
  names.add(c.component);
  const denominator=c.mapped_pull_requests;
  if(denominator>prIds.size)fail();
  if(denominator===0?c.coverage!==null:!finite(c.coverage)||Math.abs(c.coverage-c.covered_pull_requests/denominator)>1e-6)fail();
  const entries=Object.entries(c.reviewer_units);
  if(entries.some(([id,n])=>!text(id)||!count(n)||n===0||n>c.covered_pull_requests))fail();
  const total=entries.reduce((s,[,n])=>s+n,0);
  if((c.covered_pull_requests>0)!==(total>0))fail();
  if(c.reviewer_shares!==undefined){
   if(!object(c.reviewer_shares)||Object.keys(c.reviewer_shares).length!==entries.length||entries.some(([id,n])=>!finite(c.reviewer_shares[id])||Math.abs(c.reviewer_shares[id]-n/total)>1e-6))fail();
  }
  if(total===0){if(c.concentration!==null||c.risk!==null)fail();}
  else{const hhi=entries.reduce((s,[,n])=>s+(n/total)**2,0);if(!finite(c.concentration)||Math.abs(c.concentration-hhi)>1e-6||c.risk!==riskOf(c.concentration))fail();}
 }
 reconcileReviews(review,fail);
}
export function exportReport(report){return JSON.stringify(validateReport(report),null,2);}
export function importReport(json){return validateReport(JSON.parse(json));}
export function validateReport(r){
 const fail=()=>{throw Error('Select a valid continuity analyze JSON report. Person and departure exports are not supported here.');};
 if(!r||!['experimental-v0.1','experimental-v0.2'].includes(r.model)||!Array.isArray(r.components)||typeof r.revision!=='string'||typeof r.as_of!=='string'||!Number.isFinite(Date.parse(r.as_of))||!Number.isInteger(r.commit_count)||r.commit_count<0)fail();
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
 if(r.report_version!==undefined&&!['1.0','2.0'].includes(r.report_version))fail();
 if(r.review_evidence!==undefined){if(r.report_version!=='2.0')fail();validateReviews(r.review_evidence,fail);}
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
export function demoReport(){
 const people=[['Alex Morgan','alex@example.test'],['Jordan Lee','jordan@example.test'],['Casey Patel','casey@example.test'],['Sam Rivera','sam@example.test']];
 const components=[['src/payments',[.92,.08]],['src/identity',[.78,.22]],['src/catalog',[.53,.32,.15]],['src/checkout',[.40,.30,.20,.10]],['src/notifications',[.34,.33,.33]],['tests/integration',[.25,.25,.25,.25]]].map(([component,shares],i)=>{
  const contributors=shares.map((share,j)=>({contributor:people[(i+j)%4][1],name:people[(i+j)%4][0],share,score:share,commits:Math.round(share*100),files:[`${component}/shared.cs`,`${component}/area-${j}.cs`],signals:{change_ownership:share,recency:.86-j*.12,change_frequency:share,code_area_breadth:.5,unique_contribution:.25,historical_persistence:.8-j*.1}}));
  const concentration=shares.reduce((s,x)=>s+x*x,0);return{component,concentration,risk:riskOf(concentration),contributors};
 });
 return{model:'experimental-v0.1',revision:'synthetic-demo',as_of:'2026-09-01T00:00:00+00:00',commit_count:240,shallow:false,components,configuration:{component_depth:2},filters:{exclude_bots:false,exclude_generated:false}};
}
