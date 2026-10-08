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
const traceStates=['VERIFIED','PARTIAL','MISSING','UNAVAILABLE'];
const traceCapabilities=['SUPPORTED','UNSUPPORTED','UNKNOWN'];
const traceKinds=['WORK_ITEM','PULL_REQUEST','COMMIT','CHANGED_PATH','PR_PATH','COMPONENT'];
const traceRelations=['WI_PR','WI_COMMIT','PR_COMMIT','COMMIT_PATH','PR_PATH','PATH_COMPONENT','WI_COMPONENT'];
const traceOrigins=['DIRECT_PROVIDER_LINK','DIRECT_SOURCE_LINK','DERIVED_LINK'];
const traceReasons=['NO_OBSERVED_LINK','INCOMPLETE_LOOKUP','LOOKUP_UNAVAILABLE','CAPABILITY_UNAVAILABLE','OUTSIDE_BOUNDARY','INCOMPATIBLE_BOUNDARY','INVALID_OBSERVATION','CONFLICTING_OBSERVATION','UNSUPPORTED_RELATION','UNRESOLVED_NORMATIVE_SEGMENT','EMPTY_POPULATION'];
const tracePopulations=['WORK_ITEMS','PULL_REQUESTS','COMMITS','CHANGES'];
const directions=['OUTBOUND','INBOUND'];
const exact=(v,keys)=>object(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
const safeToken=v=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(v);
// Trace timestamps use a strict Gregorian ISO subset and preserve microseconds.
const traceInstant=value=>{
 if(typeof value!=='string')return null;
 const match=/^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?(Z|([+-])([0-9]{2}):([0-9]{2}))$/.exec(value);
 if(!match)return null;
 const [year,month,day,hour,minute,second]=match.slice(1,7).map(Number);
 const leap=year%4===0&&(year%100!==0||year%400===0),days=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
 if(year<1||month<1||month>12||day<1||day>days[month-1]||hour>23||minute>59||second>59||Number(match[10]??0)>23||Number(match[11]??0)>59)return null;
 const millis=Date.parse(`${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}:${match[6]}${match[8]}`);
 if(!Number.isFinite(millis))return null;
 const instant=BigInt(millis)*1000n+BigInt((match[7]??'').padEnd(6,'0'));
 return instant>=-62135596800000000n&&instant<=253402300799999999n?instant:null;
};
const traceTimestamp=value=>traceInstant(value)!==null;
const privateTraceValue=/(?:gh[pousr]_|github_pat_|glpat-|sk-[A-Za-z0-9_-]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|(?:authorization|bearer|password|passwd|cookie|set-cookie|pat|token|secret)[=: ]|(?:authorization|bearer|password|cookie|pat|token|secret)_SENTINEL|https?:\/\/|file:\/\/|(?:^|\/)(?:Users|home|tmp|private\/var|var\/tmp)\/)/i;
function publicTraceValues(value,depth=0){
 if(depth>100)return false;
 if(typeof value==='string'){
  if(privateTraceValue.test(value))return false;
  // Reject unpaired surrogate code points, which cannot form canonical UTF-8.
  for(const char of value){const code=char.codePointAt(0);if(code>=0xd800&&code<=0xdfff)return false;}
 }else if(Array.isArray(value)){return value.every(item=>publicTraceValues(item,depth+1));}
 else if(object(value)){return Object.entries(value).every(([key,item])=>publicTraceValues(key,depth+1)&&publicTraceValues(item,depth+1));}
 return true;
}
const compareText=(left,right)=>{
 const a=Array.from(left,char=>char.codePointAt(0)),b=Array.from(right,char=>char.codePointAt(0));
 for(let i=0;i<Math.min(a.length,b.length);i++)if(a[i]!==b[i])return a[i]<b[i]?-1:1;
 return Math.sign(a.length-b.length);
};
const compareTuple=(a,b)=>{
 for(let i=0;i<Math.min(a.length,b.length);i++){
  const compared=Array.isArray(a[i])?compareTuple(a[i],b[i]):typeof a[i]==='string'?compareText(a[i],b[i]):a[i]<b[i]?-1:a[i]>b[i]?1:0;
  if(compared)return compared;
 }
 return Math.sign(a.length-b.length);
};
const domainRefKey=ref=>['COMMIT','CHANGED_PATH','COMPONENT'].includes(ref.kind)?[ref.kind,ref.repository,ref.algorithm,ref.context,ref.configuration,ref.identifier]:[ref.kind,ref.provider,ref.instance,ref.scope,ref.repository,ref.context,ref.configuration,ref.identifier];
const domainLinkKey=link=>[domainRefKey(link.source),domainRefKey(link.target),link.type,link.origin];
const safePath=v=>typeof v==='string'&&v.length>0&&Array.from(v).length<=1024&&!v.startsWith('/')&&!v.includes('\\')&&!/[\u0000-\u001f\u007f:?#@]/.test(v)&&v.split('/').every(p=>p&&p!=='.'&&p!=='..');
const canonicalTraceTime=value=>{
 if(value===null)return null;const instant=traceInstant(value);if(instant===null)return value;
 const fraction=(instant%1000000n+1000000n)%1000000n,seconds=(instant-fraction)/1000000n;
 const date=new Date(Number(seconds*1000n)).toISOString().slice(0,-5);
 return date+(fraction?'.'+String(fraction).padStart(6,'0'):'')+'+00:00';
};
const stable=v=>Array.isArray(v)?v.map(stable):object(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,['collected_at','observed_at','start','end'].includes(k)?canonicalTraceTime(v[k]):stable(v[k])])):v;
const same=(a,b)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
const ordered=(values,key=value=>JSON.stringify(stable(value)))=>values.every((value,index)=>index===0||compareText(key(values[index-1]),key(value))<=0);
const compareCanonical=(a,b)=>{const left=JSON.stringify(stable(a)),right=JSON.stringify(stable(b));return compareText(left,right);};
const refFields=['kind','provider','instance','scope','identifier','repository','context','configuration','algorithm'];
const refKey=ref=>JSON.stringify(stable(ref));
const linkIdentity=link=>({source:link.source,target:link.target,type:link.type,origin:link.origin});
const linkKey=link=>JSON.stringify(stable(linkIdentity(link)));
function validateTraceability(section,fail){
 if(!publicTraceValues(section)||!exact(section,['schema_version','collection','result'])||section.schema_version!=='1.0')fail();
 const collection=section.collection,result=section.result;
 if(!exact(collection,['status','component_strategy','boundaries','work_items','populations','observed_links','lookups','diagnostics'])||!statuses.includes(collection.status))fail();
 if(!exact(collection.component_strategy,['name','configuration'])||collection.component_strategy.name!=='directory'||!/^depth-[1-9][0-9]*$/.test(collection.component_strategy.configuration))fail();
 const boundaries=new Map(), refs=new Map();
 const addRef=ref=>{const key=refKey(ref);refs.set(key,ref);return key;};
 const validRef=ref=>{
  if(!exact(ref,refFields)||!traceKinds.includes(ref.kind)||![ref.provider,ref.instance,ref.scope].every(safeToken)||typeof ref.identifier!=='string'||typeof ref.repository!=='string'||typeof ref.context!=='string'||typeof ref.configuration!=='string'||!['sha1','sha256'].includes(ref.algorithm))return false;
  if(ref.kind==='WORK_ITEM')return safeToken(ref.identifier)&&ref.repository===''&&ref.context===''&&ref.configuration===''&&ref.algorithm==='sha1';
  if(!safeToken(ref.repository))return false;
  if(ref.kind==='PULL_REQUEST')return safeToken(ref.identifier)&&!ref.context&&!ref.configuration&&ref.algorithm==='sha1';
  if(ref.kind==='COMMIT')return ref.provider==='source'&&ref.instance==='offline'&&ref.scope==='git'&&new RegExp(`^[0-9a-f]{${ref.algorithm==='sha1'?40:64}}$`).test(ref.identifier)&&!ref.context&&!ref.configuration;
  if(ref.kind==='CHANGED_PATH')return ref.provider==='source'&&ref.instance==='offline'&&ref.scope==='git'&&safePath(ref.identifier)&&new RegExp(`^[0-9a-f]{${ref.algorithm==='sha1'?40:64}}$`).test(ref.context)&&!ref.configuration;
  if(ref.kind==='PR_PATH')return safePath(ref.identifier)&&safeToken(ref.context)&&!ref.configuration&&ref.algorithm==='sha1';
  return ref.provider==='source'&&ref.instance==='offline'&&ref.scope==='components'&&(ref.identifier==='(root)'||safePath(ref.identifier))&&ref.context==='directory'&&ref.configuration===collection.component_strategy.configuration&&ref.algorithm==='sha1';
 };
 if(!Array.isArray(collection.boundaries)||!Array.isArray(collection.work_items)||!exact(collection.populations,['pull_requests','merged_pull_requests','commits','changed_paths'])||!Array.isArray(collection.observed_links)||!Array.isArray(collection.lookups)||!Array.isArray(collection.diagnostics))fail();
 const boundaryFields=['identifier','provider','instance','project','repository','collected_at','snapshot','query','identity_mapping','filter_policy','revision','time_field','start','end','normalization_version','join_contract'];
 for(const boundary of collection.boundaries){
  if(!exact(boundary,boundaryFields)||![boundary.identifier,boundary.provider,boundary.instance,boundary.project,boundary.repository,boundary.snapshot,boundary.query,boundary.identity_mapping,boundary.filter_policy,boundary.normalization_version].every(safeToken)||!traceTimestamp(boundary.collected_at))fail();
  if((boundary.revision!==null&&(typeof boundary.revision!=='string'||!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(boundary.revision)))||(boundary.time_field!==null&&!safeToken(boundary.time_field))||(boundary.join_contract!==null&&!safeToken(boundary.join_contract)))fail();
  if((boundary.start===null)!==(boundary.end===null)||(boundary.start!==null&&(!traceTimestamp(boundary.start)||!traceTimestamp(boundary.end)||traceInstant(boundary.start)>=traceInstant(boundary.end)||boundary.time_field===null)))fail();
  if(boundaries.has(boundary.identifier))fail();boundaries.set(boundary.identifier,boundary);
 }
 if(!ordered(collection.boundaries,item=>item.identifier))fail();
 const itemTypes=['REQUIREMENT','STORY','BUG','TASK','OTHER','UNKNOWN'],itemStates=['OPEN','ACTIVE','CLOSED','OTHER','UNKNOWN'];
 const itemRefs=new Set();
 for(const item of collection.work_items){
  if(!exact(item,['reference','type','state','provenance'])||!validRef(item.reference)||item.reference.kind!=='WORK_ITEM'||!itemTypes.includes(item.type)||!itemStates.includes(item.state))fail();
  if(!validObservation(item.provenance)||!boundaries.has(item.provenance.boundary))fail();
  const boundary=boundaries.get(item.provenance.boundary);if(item.reference.provider!==boundary.provider||item.reference.instance!==boundary.instance||item.reference.scope!==boundary.project)fail();
  const key=addRef(item.reference);if(itemRefs.has(key))fail();itemRefs.add(key);
 }
 if(!ordered(collection.work_items,item=>refKey(item.reference)))fail();
 function validObservation(observation){return exact(observation,['identifier','boundary','observed_at','basis'])&&[observation.identifier,observation.boundary,observation.basis].every(safeToken)&&traceTimestamp(observation.observed_at);}
 const populationRefs=new Map();
 for(const [name,kind] of [['pull_requests','PULL_REQUEST'],['merged_pull_requests','PULL_REQUESTS'],['commits','COMMIT'],['changed_paths','CHANGED_PATH']]){
  const list=collection.populations[name];if(!Array.isArray(list))fail();const seen=new Set();
  for(const ref of list){if(!validRef(ref)||ref.kind!==(kind==='PULL_REQUESTS'?'PULL_REQUEST':kind))fail();const key=addRef(ref);if(seen.has(key))fail();seen.add(key);}
  if(!ordered(list,refKey))fail();
  populationRefs.set(name,seen);
 }
 for(const key of populationRefs.get('merged_pull_requests'))if(!populationRefs.get('pull_requests').has(key))fail();
 const isPopulationRef=ref=>itemRefs.has(refKey(ref))||[...populationRefs.values()].some(values=>values.has(refKey(ref)));
 const endpoints={WI_PR:['WORK_ITEM','PULL_REQUEST'],WI_COMMIT:['WORK_ITEM','COMMIT'],PR_COMMIT:['PULL_REQUEST','COMMIT'],COMMIT_PATH:['COMMIT','CHANGED_PATH'],PR_PATH:['PULL_REQUEST','PR_PATH'],PATH_COMPONENT:[['CHANGED_PATH','PR_PATH'],'COMPONENT'],WI_COMPONENT:['WORK_ITEM','COMPONENT']};
 const linkMap=new Map();
 function checkLink(link,derivedExpected){
  if(!exact(link,['source','target','type','origin','observations','supports'])||!traceRelations.includes(link.type)||!traceOrigins.includes(link.origin)||!validRef(link.source)||!validRef(link.target)||!Array.isArray(link.observations)||!Array.isArray(link.supports))fail();
  const [sourceKinds,targetKind]=endpoints[link.type];
  if(!(Array.isArray(sourceKinds)?sourceKinds.includes(link.source.kind):link.source.kind===sourceKinds)||link.target.kind!==targetKind)fail();
  const derived=link.type==='PATH_COMPONENT'||link.type==='WI_COMPONENT';
  if(derived!==derivedExpected||(derived&&link.origin!=='DERIVED_LINK')||(!derived&&link.origin==='DERIVED_LINK'))fail();
  const legalOrigins=link.type==='COMMIT_PATH'?['DIRECT_SOURCE_LINK','DIRECT_PROVIDER_LINK']:link.type==='PATH_COMPONENT'||link.type==='WI_COMPONENT'?['DERIVED_LINK']:['DIRECT_PROVIDER_LINK'];
  if(!legalOrigins.includes(link.origin)||refKey(link.source)===refKey(link.target))fail();
  if(derived){if(link.observations.length||!link.supports.length)fail();}
  else if(!link.observations.length||link.supports.length)fail();
  for(const observation of link.observations){
   if(!validObservation(observation)||!boundaries.has(observation.boundary))fail();
   const boundary=boundaries.get(observation.boundary);
   for(const ref of [link.source,link.target]){
    if(ref.repository&&ref.repository!==boundary.repository)fail();
    if(ref.kind==='WORK_ITEM'&&(ref.provider!==boundary.provider||ref.instance!==boundary.instance||ref.scope!==boundary.project))fail();
    if(['PULL_REQUEST','PR_PATH'].includes(ref.kind)&&(ref.provider!==boundary.provider||ref.instance!==boundary.instance||ref.scope!==boundary.repository))fail();
   }
  }
  const key=linkKey(link);if(linkMap.has(key))fail();linkMap.set(key,link);
 }
 for(const link of collection.observed_links)checkLink(link,false);
 if(!ordered(collection.observed_links))fail();
 const observationKeys=new Set();
 for(const [key,link] of linkMap){
  const withinLink=new Set();
  if(!link.observations.every((observation,index)=>index===0||compareTuple([link.observations[index-1].boundary,link.observations[index-1].identifier,traceInstant(link.observations[index-1].observed_at),link.observations[index-1].basis],[observation.boundary,observation.identifier,traceInstant(observation.observed_at),observation.basis])<=0))fail();
  for(const observation of link.observations){const observationKey=observation.boundary+':'+observation.identifier;if(withinLink.has(observationKey)||observationKeys.has(observationKey))fail();withinLink.add(observationKey);observationKeys.add(observationKey);}
  if(link.type==='COMMIT_PATH'&&(link.source.repository!==link.target.repository||link.source.identifier!==link.target.context||link.source.algorithm!==link.target.algorithm))fail();
  if(link.type==='PR_PATH'&&(link.source.repository!==link.target.repository||link.source.identifier!==link.target.context))fail();
 }
 const sameInstant=(left,right)=>left===right||(left!==null&&right!==null&&traceInstant(left)===traceInstant(right));
 const compatibleBoundaries=(left,right)=>left.repository===right.repository&&left.identity_mapping===right.identity_mapping&&left.filter_policy===right.filter_policy&&(left.revision===null||right.revision===null||left.revision===right.revision)&&left.join_contract===right.join_contract&&((left.query===right.query&&left.time_field===right.time_field&&sameInstant(left.start,right.start)&&sameInstant(left.end,right.end))||(left.join_contract!==null));
 const eligibleLinks=collection.observed_links.filter(link=>isPopulationRef(link.source)&&(isPopulationRef(link.target)||link.target.kind==='PR_PATH')&&collection.boundaries.every(boundary=>link.observations.every(observation=>compatibleBoundaries(boundary,boundaries.get(observation.boundary)))));
 const eligibleLinkKeys=new Set(eligibleLinks.map(linkKey));
const contextDiagnostics=[...collection.diagnostics];
for(const link of collection.observed_links){
 const resolved=isPopulationRef(link.source)&&(isPopulationRef(link.target)||link.target.kind==='PR_PATH'),compatible=collection.boundaries.every(boundary=>link.observations.every(observation=>compatibleBoundaries(boundary,boundaries.get(observation.boundary))));
 if(!resolved||!compatible){const reason=!resolved?'OUTSIDE_BOUNDARY':'INCOMPATIBLE_BOUNDARY';for(const endpoint of [link.source,link.target])contextDiagnostics.push({reason,endpoint,relationship:link.type});}
}
 const excludedRefs=new Map();
 for(const link of collection.observed_links)if(!eligibleLinkKeys.has(linkKey(link)))for(const ref of [link.source,link.target])if(!isPopulationRef(ref)&&ref.kind!=='PR_PATH')excludedRefs.set(refKey(ref),ref);
 const lookupKeys=new Set();
 for(const lookup of collection.lookups){
  if(!exact(lookup,['boundary','capability','status','endpoint','relationship','direction','population'])||!boundaries.has(lookup.boundary)||!traceCapabilities.includes(lookup.capability)||!statuses.includes(lookup.status)||!directions.includes(lookup.direction))fail();
  if(lookup.population!==null){if(!tracePopulations.includes(lookup.population)||lookup.endpoint!==null||lookup.relationship!==null)fail();}
  else{
   if(!validRef(lookup.endpoint)||!traceRelations.includes(lookup.relationship))fail();
   const [sourceKinds,targetKind]=endpoints[lookup.relationship],kind=lookup.endpoint.kind;
   if(lookup.direction==='OUTBOUND'?(Array.isArray(sourceKinds)?!sourceKinds.includes(kind):kind!==sourceKinds):kind!==targetKind)fail();
   const ref=lookup.endpoint,boundary=boundaries.get(lookup.boundary);
   if((ref.repository&&ref.repository!==boundary.repository)||(ref.kind==='WORK_ITEM'&&(ref.provider!==boundary.provider||ref.instance!==boundary.instance||ref.scope!==boundary.project))||(['PULL_REQUEST','PR_PATH'].includes(ref.kind)&&(ref.provider!==boundary.provider||ref.instance!==boundary.instance||ref.scope!==boundary.repository))){if(lookup.capability!=='UNKNOWN'||!collection.diagnostics.some(diagnostic=>diagnostic.reason==='INCOMPATIBLE_BOUNDARY'&&same(diagnostic.endpoint,ref)&&diagnostic.relationship===lookup.relationship))fail();}
  }
  for(const diagnostic of collection.diagnostics){
   if((diagnostic.endpoint===null||same(diagnostic.endpoint,lookup.endpoint))&&(diagnostic.relationship===null||diagnostic.relationship===lookup.relationship)){
    if(diagnostic.reason==='INCOMPATIBLE_BOUNDARY'){if(lookup.capability!=='UNKNOWN')fail();}
    else if(lookup.status!=='PARTIAL')fail();
   }
  }
  const key=JSON.stringify(stable([lookup.endpoint?refKey(lookup.endpoint):null,lookup.relationship,lookup.direction,lookup.population]));if(lookupKeys.has(key))fail();lookupKeys.add(key);
 }
 if(!ordered(collection.lookups))fail();
 for(const diagnostic of collection.diagnostics){if(!exact(diagnostic,['reason','endpoint','relationship'])||!traceReasons.includes(diagnostic.reason)||(diagnostic.endpoint!==null&&!validRef(diagnostic.endpoint))||(diagnostic.relationship!==null&&!traceRelations.includes(diagnostic.relationship)))fail();}
 if(!ordered(collection.diagnostics)||new Set(collection.diagnostics.map(item=>JSON.stringify(stable(item)))).size!==collection.diagnostics.length)fail();
 if(collection.status==='COMPLETE'&&collection.diagnostics.length)fail();
 if(collection.status==='FAILED'&&(collection.work_items.length||collection.observed_links.length||collection.populations.commits.length))fail();
 if(!exact(result,['derivation_version','summary','direct_links','derived_links','paths','gaps','artifacts','metrics','diagnostics'])||result.derivation_version!=='offline-1'||!traceStates.includes(result.summary)||!Array.isArray(result.direct_links)||!Array.isArray(result.derived_links)||!Array.isArray(result.paths)||!Array.isArray(result.gaps)||!Array.isArray(result.artifacts)||!Array.isArray(result.metrics)||!Array.isArray(result.diagnostics))fail();
 if(!same(result.direct_links,collection.observed_links))fail();
 for(const link of result.derived_links)checkLink(link,true);
 for(const link of result.derived_links){
  for(const support of link.supports)if(!linkMap.has(JSON.stringify(stable(support))))fail();
  if(link.type==='PATH_COMPONENT'&&!link.supports.every((support,index)=>index===0||compareTuple(domainLinkKey(link.supports[index-1]),domainLinkKey(support))<0))fail();
 }
 if(!ordered(result.derived_links))fail();
 const depth=Number(collection.component_strategy.configuration.slice('depth-'.length));
 const expectedComponent=path=>path.split('/').slice(0,-1).slice(0,depth).join('/')||'(root)';
 for(const link of result.derived_links.filter(item=>item.type==='PATH_COMPONENT')){
  if(link.target.identifier!==expectedComponent(link.source.identifier))fail();
  const expected=eligibleLinks.filter(item=>['COMMIT_PATH','PR_PATH'].includes(item.type)&&refKey(item.target)===refKey(link.source)).map(link=>JSON.stringify(stable(linkIdentity(link))));
  const actual=link.supports.map(support=>JSON.stringify(stable(support)));
  if(new Set(actual).size!==actual.length||actual.length!==expected.length||actual.some(key=>!expected.includes(key)))fail();
 }
 const expectedPathSources=new Map();
 for(const link of eligibleLinks.filter(item=>['COMMIT_PATH','PR_PATH'].includes(item.type)))expectedPathSources.set(refKey(link.target),link.target);
 const pathMappings=result.derived_links.filter(link=>link.type==='PATH_COMPONENT');
 if(pathMappings.length!==expectedPathSources.size)fail();
 for(const [key,source] of expectedPathSources){
  const mapping=pathMappings.find(link=>refKey(link.source)===key);
  const component={kind:'COMPONENT',provider:'source',instance:'offline',scope:'components',identifier:expectedComponent(source.identifier),repository:source.repository,context:'directory',configuration:collection.component_strategy.configuration,algorithm:'sha1'};
  if(!mapping||!same(mapping.target,component))fail();
 }
 const gapFields=['endpoint','relationship','direction','status','reason'];
 function checkGap(gap){
  if(!exact(gap,gapFields)||!validRef(gap.endpoint)||!traceRelations.includes(gap.relationship)||!directions.includes(gap.direction)||!traceStates.includes(gap.status)||!traceReasons.includes(gap.reason))fail();
    const reasonStatus={NO_OBSERVED_LINK:'MISSING',INCOMPLETE_LOOKUP:'PARTIAL',UNRESOLVED_NORMATIVE_SEGMENT:'PARTIAL',LOOKUP_UNAVAILABLE:'UNAVAILABLE',CAPABILITY_UNAVAILABLE:'UNAVAILABLE',OUTSIDE_BOUNDARY:'UNAVAILABLE',INCOMPATIBLE_BOUNDARY:'UNAVAILABLE',EMPTY_POPULATION:'UNAVAILABLE'}[gap.reason];
    if(reasonStatus&&gap.status!==reasonStatus)fail();
  if(gap.status==='MISSING'){
  const lookups=collection.lookups.filter(item=>item.endpoint&&refKey(item.endpoint)===refKey(gap.endpoint)&&item.relationship===gap.relationship&&item.direction===gap.direction&&item.capability==='SUPPORTED'&&item.status==='COMPLETE');
  if(!lookups.length)fail();
  const hasScopedNegative=lookups.some(lookup=>!collection.observed_links.some(link=>link.type===gap.relationship&&refKey(gap.direction==='OUTBOUND'?link.source:link.target)===refKey(gap.endpoint)&&link.observations.some(observation=>observation.boundary===lookup.boundary)));
  if(!hasScopedNegative)fail();
  }
 }
 const incompatibleCollection=collection.observed_links.some(link=>collection.boundaries.some(boundary=>link.observations.some(observation=>!compatibleBoundaries(boundary,boundaries.get(observation.boundary)))));
 const gapFor=(endpoint,relationship,direction)=>{
  const lookup=collection.lookups.find(item=>item.endpoint&&refKey(item.endpoint)===refKey(endpoint)&&item.relationship===relationship&&item.direction===direction);
  let status,reason;
  if(incompatibleCollection){status='UNAVAILABLE';reason='INCOMPATIBLE_BOUNDARY';}
  else if(!lookup||lookup.status==='FAILED'){status='UNAVAILABLE';reason='LOOKUP_UNAVAILABLE';}
  else if(lookup.capability!=='SUPPORTED'){status='UNAVAILABLE';reason='CAPABILITY_UNAVAILABLE';}
  else if(lookup.status!=='COMPLETE'){status='PARTIAL';reason='INCOMPLETE_LOOKUP';}
  else if(result.diagnostics.some(item=>item.endpoint&&refKey(item.endpoint)===refKey(endpoint)&&item.relationship===relationship&&item.reason==='OUTSIDE_BOUNDARY')){status='UNAVAILABLE';reason='OUTSIDE_BOUNDARY';}
  else{status='MISSING';reason='NO_OBSERVED_LINK';}
  return{endpoint,relationship,direction,status,reason};
 };
 const unresolvedGap=(endpoint,relationship,direction)=>({endpoint,relationship,direction,status:'PARTIAL',reason:'UNRESOLVED_NORMATIVE_SEGMENT'});
 const expectedPathGaps=path=>{
  const nodes=path.nodes,first=nodes[0],last=nodes.at(-1),links=path.supports.map(identity=>linkMap.get(JSON.stringify(stable(identity)))),gaps=[];
  const nextKind={WORK_ITEM:'WI_PR',PULL_REQUEST:'PR_COMMIT',COMMIT:'COMMIT_PATH'};
  if(nextKind[last.kind])gaps.push(gapFor(last,nextKind[last.kind],'OUTBOUND'));
  if(first.kind==='PULL_REQUEST'){
   const incoming=eligibleLinks.filter(link=>link.type==='WI_PR'&&refKey(link.target)===refKey(first));
   gaps.push(incoming.length?unresolvedGap(first,'WI_PR','INBOUND'):gapFor(first,'WI_PR','INBOUND'));
  }else if(first.kind==='COMMIT'){
   const incoming=eligibleLinks.filter(link=>link.type==='PR_COMMIT'&&refKey(link.target)===refKey(first));
   gaps.push(incoming.length?unresolvedGap(first,'PR_COMMIT','INBOUND'):gapFor(first,'PR_COMMIT','INBOUND'));
   const hasIntent=eligibleLinks.some(link=>link.type==='WI_COMMIT'&&refKey(link.target)===refKey(first))||incoming.some(commitLink=>eligibleLinks.some(link=>link.type==='WI_PR'&&refKey(link.target)===refKey(commitLink.source)));
   if(!hasIntent)gaps.push(gapFor(first,'WI_COMMIT','INBOUND'));
  }
  if(links.some(link=>link.type==='WI_COMMIT')){
   const hasPr=eligibleLinks.some(link=>link.type==='WI_PR'&&refKey(link.source)===refKey(first));
   gaps.push(hasPr?unresolvedGap(first,'WI_PR','OUTBOUND'):gapFor(first,'WI_PR','OUTBOUND'));
  }
  if(links.some(link=>link.type==='PR_PATH')){
   const pr=nodes.find(node=>node.kind==='PULL_REQUEST');
   if(pr){const hasCommits=eligibleLinks.some(link=>link.type==='PR_COMMIT'&&refKey(link.source)===refKey(pr));gaps.push(hasCommits?unresolvedGap(pr,'PR_COMMIT','OUTBOUND'):gapFor(pr,'PR_COMMIT','OUTBOUND'));}
  }
  const unique=new Map(gaps.map(gap=>[JSON.stringify(stable(gap)),gap]));
  return [...unique.values()].sort(compareCanonical);
 };
 for(const gap of result.gaps)checkGap(gap);
 if(!ordered(result.gaps))fail();
 if(new Set(result.gaps.map(gap=>JSON.stringify(stable(gap)))).size!==result.gaps.length)fail();
 const pathKeys=new Set();
 for(const path of result.paths){
  if(!exact(path,['nodes','supports','boundaries','status','gaps','rule_version'])||!Array.isArray(path.nodes)||!path.nodes.length||!Array.isArray(path.supports)||!Array.isArray(path.boundaries)||!strings(path.boundaries)||path.boundaries.some(id=>!boundaries.has(id))||!traceStates.includes(path.status)||path.rule_version!=='offline-1'||!Array.isArray(path.gaps))fail();
  const nodeKeys=path.nodes.map(ref=>{if(!validRef(ref))fail();if(['WORK_ITEM','PULL_REQUEST','COMMIT','CHANGED_PATH'].includes(ref.kind)&&!isPopulationRef(ref))fail();if(ref.kind==='PR_PATH'&&!eligibleLinks.some(link=>link.type==='PR_PATH'&&refKey(link.target)===refKey(ref)))fail();if(ref.kind==='COMPONENT'&&!result.derived_links.some(link=>link.type==='PATH_COMPONENT'&&refKey(link.target)===refKey(ref)))fail();return refKey(ref);});if(new Set(nodeKeys).size!==nodeKeys.length)fail();
  if(path.supports.length!==Math.max(0,path.nodes.length-1))fail();
  path.supports.forEach((identity,index)=>{
   const link=linkMap.get(JSON.stringify(stable(identity)));
   if(!link||refKey(link.source)!==nodeKeys[index]||refKey(link.target)!==nodeKeys[index+1])fail();
  if(!['PATH_COMPONENT','WI_COMPONENT'].includes(link.type)&&!eligibleLinkKeys.has(linkKey(link)))fail();
    const expectedType={WORK_ITEM:{PULL_REQUEST:'WI_PR',COMMIT:'WI_COMMIT'},PULL_REQUEST:{COMMIT:'PR_COMMIT',PR_PATH:'PR_PATH'},COMMIT:{CHANGED_PATH:'COMMIT_PATH'},CHANGED_PATH:{COMPONENT:'PATH_COMPONENT'},PR_PATH:{COMPONENT:'PATH_COMPONENT'}}[path.nodes[index].kind]?.[path.nodes[index+1].kind];
    if(link.type!==expectedType)fail();
  });
  const kinds=path.nodes.map(node=>node.kind),full=kinds.length===5&&same(kinds,['WORK_ITEM','PULL_REQUEST','COMMIT','CHANGED_PATH','COMPONENT']);
  if((path.status==='VERIFIED')!==full)fail();
  const localGaps=new Set();for(const gap of path.gaps){checkGap(gap);const key=JSON.stringify(stable(gap));if(localGaps.has(key))fail();localGaps.add(key);}
  if(!ordered(path.gaps))fail();
  if(!same(path.gaps,expectedPathGaps(path)))fail();
  const key=JSON.stringify(stable(path));if(pathKeys.has(key))fail();pathKeys.add(key);
 }
 if(!ordered(result.paths))fail();
 const pathEdges=[...eligibleLinks,...pathMappings],pathOutgoing=new Map(),expectedPathsByKey=new Map(),traversalDiagnostics=[];
 for(const link of pathEdges){const key=refKey(link.source);if(!pathOutgoing.has(key))pathOutgoing.set(key,[]);pathOutgoing.get(key).push(link);}
 const pathRoots=[...collection.work_items.map(item=>item.reference),...collection.populations.pull_requests,...collection.populations.commits];
 for(const root of pathRoots){
  if(!['WORK_ITEM','PULL_REQUEST','COMMIT'].includes(root.kind))continue;
  const pending=[{nodes:[root],links:[]}];
  while(pending.length){
   const current=pending.pop(),last=current.nodes.at(-1),edges=pathOutgoing.get(refKey(last))??[];
   if(edges.length){
    for(const link of [...edges].reverse()){
     if(current.nodes.some(node=>refKey(node)===refKey(link.target))||current.nodes.length>=5){traversalDiagnostics.push({reason:'INVALID_OBSERVATION',endpoint:last,relationship:link.type});continue;}
     pending.push({nodes:[...current.nodes,link.target],links:[...current.links,link]});
    }
    continue;
   }
   const full=current.nodes.length===5&&same(current.nodes.map(node=>node.kind),['WORK_ITEM','PULL_REQUEST','COMMIT','CHANGED_PATH','COMPONENT']);
   const path={nodes:current.nodes.map(ref=>ref),supports:current.links.map(linkIdentity),boundaries:[...new Set(current.links.flatMap(link=>link.observations.map(observation=>observation.boundary)))].sort(),status:full?'VERIFIED':'PARTIAL',gaps:[],rule_version:'offline-1'};
   path.gaps=expectedPathGaps(path);
   expectedPathsByKey.set(JSON.stringify(stable(path)),path);
  }
 }
 const expectedPaths=[...expectedPathsByKey.values()].sort(compareCanonical);
 if(!same(result.paths,expectedPaths))fail();
 const expectedShortcuts=new Map();
 for(const path of expectedPaths){
  if(path.nodes[0].kind!=='WORK_ITEM'||path.nodes.at(-1).kind!=='COMPONENT')continue;
  const key=refKey(path.nodes[0])+'\u0000'+refKey(path.nodes.at(-1));
  if(!expectedShortcuts.has(key))expectedShortcuts.set(key,{source:path.nodes[0],target:path.nodes.at(-1),routes:0,supports:new Map()});
  expectedShortcuts.get(key).routes++;
  for(const support of path.supports)expectedShortcuts.get(key).supports.set(JSON.stringify(stable(support)),support);
 }
 const shortcutLinks=result.derived_links.filter(link=>link.type==='WI_COMPONENT');
 if(shortcutLinks.length!==expectedShortcuts.size)fail();
 for(const expected of expectedShortcuts.values()){
  const shortcut=shortcutLinks.find(link=>refKey(link.source)===refKey(expected.source)&&refKey(link.target)===refKey(expected.target));
  const expectedSupportKeys=[...expected.supports.keys()],actualSupportKeys=shortcut?.supports.map(support=>JSON.stringify(stable(support)))??[];
  const orderedSupports=[...expected.supports.values()];if(expected.routes>1)orderedSupports.sort((a,b)=>compareTuple(domainLinkKey(a),domainLinkKey(b)));
  if(!same(shortcut?.supports,orderedSupports))fail();
  if(!shortcut||new Set(actualSupportKeys).size!==actualSupportKeys.length||actualSupportKeys.length!==expectedSupportKeys.length||actualSupportKeys.some(key=>!expected.supports.has(key)))fail();
 }
 const expectedGlobalGaps=result.paths.flatMap(path=>path.gaps);
 for(const item of collection.work_items){
  const hasOutgoing=eligibleLinks.some(link=>refKey(link.source)===refKey(item.reference));
  if(!hasOutgoing)expectedGlobalGaps.push(gapFor(item.reference,'WI_COMMIT','OUTBOUND'));
 }
 const canonicalGlobalGaps=[...new Map(expectedGlobalGaps.map(gap=>[JSON.stringify(stable(gap)),gap])).values()].sort(compareCanonical);
 if(!same(result.gaps,canonicalGlobalGaps))fail();
 for(const link of result.derived_links.filter(item=>item.type==='WI_COMPONENT')){
  const supportingPaths=result.paths.filter(path=>path.nodes[0]?.kind==='WORK_ITEM'&&refKey(path.nodes[0])===refKey(link.source)&&path.nodes.at(-1)?.kind==='COMPONENT'&&refKey(path.nodes.at(-1))===refKey(link.target));
  const actualKeys=link.supports.map(identity=>JSON.stringify(stable(identity))),expectedKeys=supportingPaths.flatMap(path=>path.supports).map(identity=>JSON.stringify(stable(identity)));
  if(!supportingPaths.length||new Set(actualKeys).size!==actualKeys.length||actualKeys.length!==new Set(expectedKeys).size||actualKeys.some(key=>!expectedKeys.includes(key)))fail();
 }
 for(const path of result.paths){
  const supportBoundaries=new Set();
  const collectBoundaries=(identity,seen=new Set())=>{
   const key=JSON.stringify(stable(identity));if(seen.has(key))fail();seen.add(key);
   const link=linkMap.get(key);if(!link)fail();
   for(const observation of link.observations)supportBoundaries.add(observation.boundary);
   for(const support of link.supports)collectBoundaries(support,seen);
  };
  for(const support of path.supports)collectBoundaries(support);
  if(!same(path.boundaries,[...supportBoundaries].sort()))fail();
 }
 const artifactKeys=new Set();
 for(const artifact of result.artifacts){if(!exact(artifact,['artifact','status'])||!validRef(artifact.artifact)||!traceStates.includes(artifact.status))fail();const key=refKey(artifact.artifact);if(artifactKeys.has(key))fail();artifactKeys.add(key);}
 if(!ordered(result.artifacts,item=>refKey(item.artifact)))fail();
 const metricDimensions=['merged_pr_intent','commit_intent','component_change_intent','work_item_implementation'],metricKeys=new Set();
 for(const metric of result.metrics){
  if(!exact(metric,['dimension','numerator','denominator','value','status','collection_status','boundaries','sources','unknown_count','excluded_count','reason','component'])||!metricDimensions.includes(metric.dimension)||!count(metric.numerator)||!count(metric.denominator)||metric.numerator>metric.denominator||!traceStates.includes(metric.status)||!statuses.includes(metric.collection_status)||metric.collection_status!==collection.status||!Array.isArray(metric.boundaries)||!strings(metric.boundaries)||metric.boundaries.some(id=>!boundaries.has(id))||!same(metric.boundaries,collection.boundaries.map(boundary=>boundary.identifier))||!Array.isArray(metric.sources)||!metric.sources.every(safeToken)||!same(metric.sources,[...new Set(collection.boundaries.map(boundary=>boundary.provider))].sort())||!count(metric.unknown_count)||!count(metric.excluded_count)||(metric.reason!==null&&!traceReasons.includes(metric.reason))||(metric.component!==null&&(!validRef(metric.component)||metric.component.kind!=='COMPONENT')))fail();
  if((metric.dimension==='component_change_intent')!==(metric.component!==null))fail();
  if(metric.denominator===0){if(metric.numerator!==0||metric.value!==null||metric.status!=='UNAVAILABLE')fail();}
  else if(metric.status==='UNAVAILABLE'){if(metric.value!==null)fail();}
  else if(!finite(metric.value,0,1)||metric.value!==metric.numerator/metric.denominator)fail();
  if(metric.status==='VERIFIED'&&metric.numerator!==metric.denominator)fail();
  if(metric.status==='MISSING'&&metric.numerator!==0)fail();
  const key=metric.dimension+':'+(metric.component?refKey(metric.component):'');if(metricKeys.has(key))fail();metricKeys.add(key);
 }
 if(!ordered(result.metrics))fail();
 const workItemKeys=new Set(collection.work_items.map(item=>refKey(item.reference))),mergedPrKeys=populationRefs.get('merged_pull_requests'),commitKeys=populationRefs.get('commits');
 const intentPrKeys=new Set(eligibleLinks.filter(link=>link.type==='WI_PR'&&workItemKeys.has(refKey(link.source))).map(link=>refKey(link.target)));
 const intentCommitKeys=new Set(eligibleLinks.filter(link=>link.type==='WI_COMMIT'&&workItemKeys.has(refKey(link.source))).map(link=>refKey(link.target)));
 for(const link of eligibleLinks)if(link.type==='PR_COMMIT'&&intentPrKeys.has(refKey(link.source)))intentCommitKeys.add(refKey(link.target));
 const implementedWorkItems=new Set(result.paths.filter(path=>path.nodes[0]?.kind==='WORK_ITEM'&&path.nodes.at(-1)?.kind==='COMPONENT'&&path.nodes.some(node=>node.kind==='COMMIT')).map(path=>refKey(path.nodes[0])));
 const mappedChanges=new Map();
 for(const link of eligibleLinks.filter(item=>item.type==='COMMIT_PATH')){
  const mapping=result.derived_links.find(item=>item.type==='PATH_COMPONENT'&&refKey(item.source)===refKey(link.target));
  if(mapping){if(!mappedChanges.has(refKey(mapping.target)))mappedChanges.set(refKey(mapping.target),new Map());mappedChanges.get(refKey(mapping.target)).set(refKey(link.target),refKey(link.source));}
 }
 const expectedMetrics=new Map([
  ['merged_pr_intent\u0000',[new Set([...intentPrKeys].filter(key=>mergedPrKeys.has(key))).size,mergedPrKeys.size]],
  ['commit_intent\u0000',[new Set([...intentCommitKeys].filter(key=>commitKeys.has(key))).size,commitKeys.size]],
  ['work_item_implementation\u0000',[new Set([...implementedWorkItems].filter(key=>workItemKeys.has(key))).size,workItemKeys.size]],
 ]);
 for(const [component,changes] of mappedChanges)expectedMetrics.set('component_change_intent\u0000'+component,[new Set([...changes].filter(([,commit])=>intentCommitKeys.has(commit)).map(([path])=>path)).size,changes.size]);
 if(result.metrics.length!==expectedMetrics.size)fail();
 for(const metric of result.metrics){
  const key=metric.dimension+'\u0000'+(metric.component?refKey(metric.component):''),counts=expectedMetrics.get(key);
  if(!counts||metric.numerator!==counts[0]||metric.denominator!==counts[1])fail();
  const excluded=new Set();
  const addExcluded=ref=>{if(ref.kind===({merged_pr_intent:'PULL_REQUEST',commit_intent:'COMMIT',work_item_implementation:'WORK_ITEM',component_change_intent:'CHANGED_PATH'}[metric.dimension]))excluded.add(refKey(ref));};
  for(const ref of excludedRefs.values()){
   if(metric.dimension==='component_change_intent'){
    if(ref.kind==='CHANGED_PATH'&&ref.repository===metric.component.repository&&expectedComponent(ref.identifier)===metric.component.identifier)excluded.add(refKey(ref));
   }else addExcluded(ref);
  }
  if(metric.dimension==='merged_pr_intent')for(const ref of collection.populations.pull_requests)if(!populationRefs.get('merged_pull_requests').has(refKey(ref)))excluded.add(refKey(ref));
  if(metric.excluded_count!==excluded.size)fail();
 }
 const allPopulationRefs=[...collection.work_items.map(item=>item.reference),...collection.populations.pull_requests,...collection.populations.commits,...collection.populations.changed_paths];
 const dimensionState={
  merged_pr_intent:[['PULL_REQUESTS','WORK_ITEMS'],['WI_PR']],
  commit_intent:[['COMMITS','WORK_ITEMS','PULL_REQUESTS'],['WI_PR','WI_COMMIT','PR_COMMIT']],
  component_change_intent:[['CHANGES','COMMITS','WORK_ITEMS','PULL_REQUESTS'],['WI_PR','WI_COMMIT','PR_COMMIT','COMMIT_PATH']],
  work_item_implementation:[['WORK_ITEMS','COMMITS','CHANGES','PULL_REQUESTS'],['WI_PR','WI_COMMIT','PR_COMMIT','COMMIT_PATH']],
 };
 function stateFor(populations,relations){
  const selected=populations.map(population=>collection.lookups.find(lookup=>lookup.population===population));
  selected.push(...collection.lookups.filter(lookup=>relations.includes(lookup.relationship)));
  let available=!result.diagnostics.some(diagnostic=>diagnostic.reason==='INCOMPATIBLE_BOUNDARY')&&selected.every(lookup=>lookup&&lookup.capability==='SUPPORTED'&&lookup.status!=='FAILED');
  let complete=collection.status==='COMPLETE'&&selected.every(lookup=>lookup&&lookup.status==='COMPLETE');
  for(const relation of relations){
   const [sourceKinds,targetKind]=endpoints[relation];
   for(const ref of allPopulationRefs){
    const direction=Array.isArray(sourceKinds)?(sourceKinds.includes(ref.kind)?'OUTBOUND':null):(ref.kind===sourceKinds?'OUTBOUND':ref.kind===targetKind?'INBOUND':null);
    const applies=Array.isArray(sourceKinds)?(sourceKinds.includes(ref.kind)||ref.kind===targetKind):direction!==null;
    if(!applies)continue;
    const lookup=collection.lookups.find(item=>item.endpoint&&refKey(item.endpoint)===refKey(ref)&&item.relationship===relation&&item.direction===(direction??'INBOUND'));
    if(!lookup||lookup.capability!=='SUPPORTED'||lookup.status==='FAILED')available=false;
    if(!lookup||lookup.status!=='COMPLETE')complete=false;
   }
  }
  return{available,complete};
 }
 for(const metric of result.metrics){
  const [populations,relations]=dimensionState[metric.dimension],{available,complete}=stateFor(populations,relations);
  const expectedStatus=!available||metric.denominator===0?'UNAVAILABLE':!complete?'PARTIAL':metric.numerator===0?'MISSING':metric.numerator===metric.denominator?'VERIFIED':'PARTIAL';
  const expectedReason=metric.denominator===0?'EMPTY_POPULATION':!available?'CAPABILITY_UNAVAILABLE':!complete?'INCOMPLETE_LOOKUP':null;
  const expectedUnknown=available&&complete?0:metric.denominator-metric.numerator;
  const expectedValue=available&&metric.denominator>0?metric.numerator/metric.denominator:null;
  if(metric.status!==expectedStatus||metric.reason!==expectedReason||metric.unknown_count!==expectedUnknown||metric.value!==expectedValue)fail();
 }
 const observedChanges=new Set(eligibleLinks.filter(link=>link.type==='COMMIT_PATH').map(link=>refKey(link.target)));
 const verifiedChanges=new Set(result.paths.filter(path=>path.status==='VERIFIED').flatMap(path=>path.nodes.filter(node=>node.kind==='CHANGED_PATH').map(refKey)));
 const summaryState=stateFor(['WORK_ITEMS','PULL_REQUESTS','COMMITS','CHANGES'],['WI_PR','PR_COMMIT','COMMIT_PATH']);
 const expectedSummary=!summaryState.available||observedChanges.size===0?'UNAVAILABLE':!summaryState.complete?'PARTIAL':verifiedChanges.size===0?'MISSING':verifiedChanges.size===observedChanges.size?'VERIFIED':'PARTIAL';
 if(result.summary!==expectedSummary)fail();
 const expectedArtifacts=new Set([...allPopulationRefs.map(refKey),...result.derived_links.filter(link=>link.type==='PATH_COMPONENT').map(link=>refKey(link.target))]);
 if(expectedArtifacts.size!==artifactKeys.size||[...expectedArtifacts].some(key=>!artifactKeys.has(key)))fail();
 for(const artifact of result.artifacts){
  const key=refKey(artifact.artifact),relatedPaths=result.paths.filter(path=>path.nodes.some(node=>refKey(node)===key)),relatedGaps=result.gaps.filter(gap=>refKey(gap.endpoint)===key);
  let expectedStatus;
  if(artifact.artifact.kind==='COMPONENT'){
  const occurrences=new Set();for(const link of eligibleLinks.filter(item=>item.type==='COMMIT_PATH')){
    if(result.derived_links.some(mapping=>mapping.type==='PATH_COMPONENT'&&refKey(mapping.source)===refKey(link.target)&&refKey(mapping.target)===key))occurrences.add(refKey(link.target));
   }
   const full=new Set(result.paths.filter(path=>path.status==='VERIFIED').flatMap(path=>path.nodes.filter(node=>node.kind==='CHANGED_PATH'&&result.derived_links.some(mapping=>mapping.type==='PATH_COMPONENT'&&refKey(mapping.source)===refKey(node)&&refKey(mapping.target)===key)).map(refKey)));
   expectedStatus=!summaryState.available||occurrences.size===0?'UNAVAILABLE':!summaryState.complete?'PARTIAL':full.size===0?'MISSING':full.size===occurrences.size?'VERIFIED':'PARTIAL';
  }else if(relatedPaths.some(path=>path.status==='VERIFIED'))expectedStatus='VERIFIED';
  else if(relatedPaths.some(path=>path.supports.length))expectedStatus='PARTIAL';
  else if(relatedGaps.some(gap=>gap.status==='UNAVAILABLE'))expectedStatus='UNAVAILABLE';
  else if(relatedGaps.some(gap=>gap.status==='PARTIAL'))expectedStatus='PARTIAL';
  else expectedStatus=!summaryState.available?'UNAVAILABLE':!summaryState.complete?'PARTIAL':'MISSING';
  if(artifact.status!==expectedStatus)fail();
 }
 for(const diagnostic of result.diagnostics){if(!exact(diagnostic,['reason','endpoint','relationship'])||!traceReasons.includes(diagnostic.reason)||(diagnostic.endpoint!==null&&!validRef(diagnostic.endpoint))||(diagnostic.relationship!==null&&!traceRelations.includes(diagnostic.relationship)))fail();}
 const expectedDiagnostics=[...new Map([...contextDiagnostics,...traversalDiagnostics].map(item=>[JSON.stringify(stable(item)),item])).values()].sort(compareCanonical);
 if(!same(result.diagnostics,expectedDiagnostics))fail();
 if(collection.status==='FAILED'&&!collection.observed_links.length&&!collection.work_items.length&&result.summary!=='UNAVAILABLE')fail();
}
const reportError=()=>Error('Select a valid continuity analyze JSON report. Person and departure exports are not supported here.');
// JSON.parse discards duplicate object keys. Check them before accepting a report.
function uniqueJsonObjects(json){
 if(typeof json!=='string')throw reportError();
 let index=0;
 const space=()=>{while(/[ \t\r\n]/.test(json[index]??'')&&index<json.length)index++;};
 const string=()=>{
  const start=index++;while(index<json.length){const char=json[index++];if(char==='\\'){index++;continue;}if(char==='"')return JSON.parse(json.slice(start,index));}
  throw reportError();
 };
 const value=depth=>{
  if(depth>100)throw reportError();space();const char=json[index];
  if(char==='"'){string();return;}
  if(char==='{'||char==='['){
   index++;space();const close=char==='{'?'}':']',keys=new Set();if(json[index]===close){index++;return;}
   for(;;){
    space();if(char==='{'){
     if(json[index]!=='"')throw reportError();const key=string();if(keys.has(key))throw reportError();keys.add(key);
     space();if(json[index++]!==':')throw reportError();
    }
    value(depth+1);space();if(json[index]===close){index++;return;}if(json[index++]!==',')throw reportError();
   }
  }
  const token=/^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(json.slice(index));
  if(!token)throw reportError();index+=token[0].length;
 };
 value(0);space();if(index!==json.length)throw reportError();
}
export function exportReport(report){try{return JSON.stringify(validateReport(report),null,2);}catch{throw reportError();}}
export function importReport(json){try{uniqueJsonObjects(json);return validateReport(JSON.parse(json));}catch{throw reportError();}}
export function validateReport(r){try{return validateReportValue(r);}catch{throw reportError();}}
function validateReportValue(r){
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
 if(r.report_version!==undefined&&!['1.0','2.0','3.0'].includes(r.report_version))fail();
 if(r.report_version==='3.0'&&r.model!=='experimental-v0.1')fail();
 if(r.review_evidence!==undefined){if(!['2.0','3.0'].includes(r.report_version))fail();validateReviews(r.review_evidence,fail);}
 if(r.traceability_evidence!==undefined){if(r.report_version!=='3.0'||r.model!=='experimental-v0.1')fail();validateTraceability(r.traceability_evidence,fail);}
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
