import {publicSchemas} from './portable-public.js';
/** Portable v4 validation: explicit allowlist, exact snapshot and pure recomputation. */
import {exact,safeToken,publicTraceValues,traceTimestamp,canonicalTraceTime,domainRefKey,compareTuple,compareCanonical,same,stable,safePath,refFields} from './model.js';
const kinds=['REQUIREMENT','ARCHITECTURE_DOCUMENT','TEST','VERIFICATION'];
const relations={REQUIREMENT_WORK_ITEM:['REQUIREMENT','WORK_ITEM'],DOCUMENT_REQUIREMENT:['ARCHITECTURE_DOCUMENT','REQUIREMENT'],DOCUMENT_COMPONENT:['ARCHITECTURE_DOCUMENT','COMPONENT'],TEST_REQUIREMENT:['TEST','REQUIREMENT'],VERIFICATION_TEST:['VERIFICATION','TEST']};
const statuses=['COMPLETE','PARTIAL','FAILED'],caps=['SUPPORTED','UNSUPPORTED','UNKNOWN'],outcomes=['PASS','FAIL','SKIPPED','UNKNOWN'];
const collectionKeys=['artifacts','associations','runs','lookups','snapshot','boundary','collected_at','status','limits'];
const resultKeys=['rule_version','snapshot_valid','requirements','paths','runs','metrics','outcomes','gaps','diagnostics','dropped','associations','collection_status'];
const refKey=r=>[r.kind,r.document_kind,r.instance,r.scope,r.identifier,r.version];
const endKey=r=>kinds.includes(r.kind)?['v0.4',...refKey(r)]:['v0.3',...domainRefKey(r)];
const assocKey=a=>[endKey(a.source),endKey(a.target),a.relation,a.origin,a.boundary];
const lookupKey=l=>[l.population??'',l.relation??'',l.direction,...(l.endpoint?refKey(l.endpoint):[])];
const key=v=>JSON.stringify(stable(v));
const unique=values=>[...new Map(values.map(v=>[key(v),v])).values()];
const memberships=new WeakMap();
const has=(values,value)=>{let indexed=memberships.get(values);if(!indexed){indexed=new Set(values.map(key));memberships.set(values,indexed);}return indexed.has(key(value));};
const count=v=>Number.isSafeInteger(v)&&v>=0;
function validNew(r){return exact(r,['kind','instance','scope','identifier','version','document_kind'])&&kinds.includes(r.kind)&&[r.instance,r.scope,r.identifier,r.version].every(safeToken)&&(r.kind==='ARCHITECTURE_DOCUMENT'?['ADR','ICD'].includes(r.document_kind):r.document_kind==='');}
function validLegacy(r){
 if(!exact(r,refFields)||![r.provider,r.instance,r.scope].every(safeToken)||typeof r.identifier!=='string'||typeof r.repository!=='string'||typeof r.context!=='string'||typeof r.configuration!=='string'||!['sha1','sha256'].includes(r.algorithm))return false;
 if(r.kind==='WORK_ITEM')return safeToken(r.identifier)&&!r.repository&&!r.context&&!r.configuration&&r.algorithm==='sha1';
 return r.kind==='COMPONENT'&&r.provider==='source'&&r.instance==='offline'&&r.scope==='components'&&safeToken(r.repository)&&(r.identifier==='(root)'||safePath(r.identifier))&&r.context==='directory'&&safeToken(r.configuration)&&r.algorithm==='sha1';
}
function validSnapshot(s){return exact(s,['alias','repository','revision','fingerprint'])&&safeToken(s.alias)&&safeToken(s.repository)&&/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(s.revision)&&/^[a-f0-9]{64}$/.test(s.fingerprint);}
// SHA-256 over UTF-8, project-owned synchronous implementation for offline validator.
export function sha256(text){
 const bytes=new TextEncoder().encode(text),length=bytes.length,padded=new Uint8Array(Math.ceil((length+9)/64)*64);padded.set(bytes);padded[length]=128;
 const view=new DataView(padded.buffer);view.setUint32(padded.length-8,Math.floor(length*8/2**32));view.setUint32(padded.length-4,length*8>>>0);
 const primes=[],initial=[],constants=[];for(let n=2;primes.length<64;n++){if(primes.every(p=>n%p)){primes.push(n);if(initial.length<8)initial.push(Math.floor((Math.sqrt(n)%1)*2**32)>>>0);constants.push(Math.floor((Math.cbrt(n)%1)*2**32)>>>0);}}
 const h=initial,w=new Uint32Array(64),rotate=(x,n)=>(x>>>n)|(x<<(32-n));
 for(let offset=0;offset<padded.length;offset+=64){for(let i=0;i<16;i++)w[i]=view.getUint32(offset+i*4);for(let i=16;i<64;i++){const x=w[i-15],y=w[i-2];w[i]=(w[i-16]+(rotate(x,7)^rotate(x,18)^(x>>>3))+w[i-7]+(rotate(y,17)^rotate(y,19)^(y>>>10)))>>>0;}
 let [a,b,c,d,e,f,g,hh]=h;for(let i=0;i<64;i++){const t1=(hh+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+w[i])>>>0,t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;hh=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}[a,b,c,d,e,f,g,hh].forEach((v,i)=>h[i]=(h[i]+v)>>>0);}
 return h.map(v=>v.toString(16).padStart(8,'0')).join('');
}
const ascii=s=>JSON.stringify(s).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
// Existing Python traceability canonical JSON owns floating metric value spellings.
function pythonTraceJSON(v,field=''){if(v===null)return'null';if(typeof v==='string')return ascii(v);if(typeof v==='number'){if(field!=='value')return String(v);if(v!==0&&(Math.abs(v)<1e-4||Math.abs(v)>=1e16))return v.toExponential().replace(/e([+-])(\d)$/, 'e$10$2');return String(v)+(Number.isInteger(v)?'.0':'');}if(typeof v==='boolean')return String(v);if(Array.isArray(v))return'['+v.map(x=>pythonTraceJSON(x)).join(',')+']';return'{'+Object.keys(v).sort().map(k=>ascii(k)+':'+pythonTraceJSON(v[k],k)).join(',')+'}';}
export function derivePortable(raw,code){
 const c=stable(raw),diagnostics=[],diagnosticKeys=new Set(),diag=(reason,endpoint=null,relation=null)=>{const d={reason,endpoint,relation},k=key(d);if(!diagnosticKeys.has(k)){diagnosticKeys.add(k);diagnostics.push(d);}};
 const dropped={},limited=(name,values,max)=>{dropped[name]=Math.max(0,values.length-max);if(dropped[name])diag('LIMIT_EXHAUSTED');return values.slice(0,max);};
 const artifacts=limited('artifacts',unique(c.artifacts).sort((a,b)=>compareTuple(refKey(a),refKey(b))),c.limits.artifacts);
 const byKind=Object.fromEntries(kinds.map(k=>[k,artifacts.filter(a=>a.kind===k)]));
 const groups=new Map();for(const r of unique(c.runs)){const k=key(refKey(r.reference));if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}
 const conflictedTests=[];for(const values of groups.values())if(values.length>1){diag('CONFLICTING_OBSERVATION',values[0].reference,'VERIFICATION_TEST');conflictedTests.push(...values.map(r=>r.test));}
 const runKey=r=>[refKey(r.reference),refKey(r.test),r.target.alias,r.target.repository,r.target.revision,r.target.fingerprint,r.observed_at,r.outcome,r.boundary,r.group??''];
 const runs=limited('runs',[...groups.values()].filter(v=>v.length===1).map(v=>v[0]).sort((a,b)=>compareTuple(runKey(a),runKey(b))),c.limits.runs),runRefs=runs.map(r=>r.reference);
 const lookupGroups=new Map();for(const l of unique(c.lookups)){const k=key(lookupKey(l));if(!lookupGroups.has(k))lookupGroups.set(k,[]);lookupGroups.get(k).push(l);}
 const lookups=new Map();for(const [k,values] of lookupGroups){values.sort((a,b)=>compareTuple([a.status,a.capability],[b.status,b.capability]));let l={...values[0]};if(values.length>1){diag('CONFLICTING_LOOKUP',l.endpoint,l.relation);l.status='PARTIAL';l.capability='UNKNOWN';}if(l.relation==='VERIFICATION_TEST'&&has(conflictedTests,l.endpoint)){l.status='PARTIAL';l.capability='UNKNOWN';}lookups.set(k,l);}
 const bounds=code.collection.boundaries,revisions=new Set(bounds.map(b=>b.revision)),snapshotValid=bounds.length>0&&revisions.size===1&&!revisions.has(null)&&bounds.every(b=>b.repository===c.snapshot.repository&&b.revision===c.snapshot.revision)&&sha256(pythonTraceJSON(stable(code)))===c.snapshot.fingerprint;
 if(!snapshotValid)diag('SNAPSHOT_MISMATCH');
 const legacy=[...code.collection.work_items.map(w=>w.reference),...code.result.artifacts.filter(a=>a.artifact.kind==='COMPONENT').map(a=>a.artifact)];
 let associations=[];for(const a of unique(c.associations).sort((a,b)=>compareTuple(assocKey(a),assocKey(b)))){
 let resolved=has(artifacts,a.source)||has(runRefs,a.source);
 resolved=resolved&&(kinds.includes(a.target.kind)?has(artifacts,a.target):snapshotValid&&has(legacy,a.target)&&bounds.some(b=>b.project===a.source.scope));
 if(a.boundary!==c.boundary||!resolved)diag('UNRESOLVED_ASSOCIATION',a.source,a.relation);
 else if(a.relation==='VERIFICATION_TEST'&&!runs.some(r=>same(r.reference,a.source)&&same(r.test,a.target)))diag('UNRESOLVED_ASSOCIATION',a.source,a.relation);
 else associations.push(a);
 }
 associations=limited('associations',associations,c.limits.associations);
 const pathsByWI=new Map(),pathKey=p=>[p.nodes.map(endKey),p.supports.map(s=>[domainRefKey(s.source),domainRefKey(s.target),s.type,s.origin]),p.status,p.boundaries];
 for(const p of code.result.paths){const k=key(p.nodes[0]);if(!pathsByWI.has(k))pathsByWI.set(k,[]);pathsByWI.get(k).push(p);}for(const values of pathsByWI.values())values.sort((a,b)=>compareTuple(pathKey(a),pathKey(b)));
 const paths=[];let totalPaths=0;for(const a of associations)if(a.relation==='REQUIREMENT_WORK_ITEM'){const values=pathsByWI.get(key(a.target))??[];totalPaths+=values.length;for(const p of values.slice(0,Math.max(0,c.limits.paths-paths.length)))paths.push({association:a,code_path:p});}dropped.paths=totalPaths-paths.length;if(dropped.paths)diag('LIMIT_EXHAUSTED');
 const qualified=runs.map(r=>{const reason=r.boundary!==c.boundary?'BOUNDARY_MISMATCH':!has(artifacts,r.test)?'UNOBSERVED_TEST_VERSION':!snapshotValid||!same(r.target,c.snapshot)?'TARGET_MISMATCH':!associations.some(a=>a.relation==='VERIFICATION_TEST'&&same(a.source,r.reference)&&same(a.target,r.test))?'UNRESOLVED_VERIFICATION':null;if(reason)diag(reason,r.test,'VERIFICATION_TEST');return{...r,qualified:reason===null,reason};});
 let status=diagnostics.length||c.status!=='COMPLETE'?'PARTIAL':'COMPLETE';if(c.status==='FAILED'&&!artifacts.length&&!associations.length&&!runs.length)status='FAILED';
 const get=(endpoint=null,relation=null,direction='OUTBOUND',population=null)=>lookups.get(key(lookupKey({endpoint,relation,direction,population})));
 const absence=(ref,relation,direction='OUTBOUND')=>{const populations=relations[relation].filter(k=>['REQUIREMENT','TEST','ARCHITECTURE_DOCUMENT'].includes(k));const required=[...populations.map(p=>get(null,null,'OUTBOUND',p)),get(ref,relation,direction)];if(required.some(l=>!l||l.capability!=='SUPPORTED'||l.status==='FAILED'))return'UNAVAILABLE';return status==='COMPLETE'&&required.every(l=>l.status==='COMPLETE')?'MISSING':'PARTIAL';};
 const codeRequirements=unique(paths.filter(p=>p.code_path.status==='VERIFIED'&&p.code_path.nodes.at(-1).kind==='COMPONENT').map(p=>p.association.source)),testRequirements=unique(associations.filter(a=>a.relation==='TEST_REQUIREMENT').map(a=>a.target)),documentRequirements=unique(associations.filter(a=>a.relation==='DOCUMENT_REQUIREMENT').map(a=>a.target)),executedTests=unique(qualified.filter(r=>r.qualified&&['PASS','FAIL'].includes(r.outcome)).map(r=>r.test));
 const requirements=byKind.REQUIREMENT.map(ref=>{const ps=paths.filter(p=>same(p.association.source,ref));return{reference:ref,implementation:!snapshotValid?'UNAVAILABLE':has(codeRequirements,ref)?'VERIFIED':ps.some(p=>p.code_path.status==='PARTIAL')?'PARTIAL':ps.some(p=>p.code_path.status==='UNAVAILABLE')?'UNAVAILABLE':absence(ref,'REQUIREMENT_WORK_ITEM'),tests:has(testRequirements,ref)?'VERIFIED':absence(ref,'TEST_REQUIREMENT','INBOUND'),architecture:has(documentRequirements,ref)?'VERIFIED':absence(ref,'DOCUMENT_REQUIREMENT','INBOUND')};});
 const gaps=[];for(const r of requirements)for(const [relation,direction,state] of [['REQUIREMENT_WORK_ITEM','OUTBOUND',r.implementation],['TEST_REQUIREMENT','INBOUND',r.tests],['DOCUMENT_REQUIREMENT','INBOUND',r.architecture]])if(state!=='VERIFIED')gaps.push({endpoint:r.reference,relation,direction,status:state,reason:relation==='REQUIREMENT_WORK_ITEM'&&!snapshotValid?'SNAPSHOT_MISMATCH':state==='MISSING'?'NO_OBSERVED_LINK':state==='UNAVAILABLE'?'LOOKUP_UNAVAILABLE':'INCOMPLETE_EVIDENCE'});
 const dimensions=[['requirement_implementation',codeRequirements,'REQUIREMENT',['REQUIREMENT'],['REQUIREMENT_WORK_ITEM'],'implementation'],['requirement_tests',testRequirements,'REQUIREMENT',['REQUIREMENT','TEST'],['TEST_REQUIREMENT'],'tests'],['requirement_architecture',documentRequirements,'REQUIREMENT',['REQUIREMENT','ARCHITECTURE_DOCUMENT'],['DOCUMENT_REQUIREMENT'],'architecture'],['executed_tests',executedTests,'TEST',['TEST'],['VERIFICATION_TEST'],null]];
 const metrics=dimensions.map(([dimension,covered,population,populations,rels,field])=>{
 const requested=populations.map(p=>get(null,null,'OUTBOUND',p));for(const relation of rels){const [source,target]=relations[relation];for(const a of [...artifacts,...runRefs])if(a.kind===source)requested.push(get(a,relation));else if(a.kind===target)requested.push(get(a,relation,'INBOUND'));}
 let available=requested.every(l=>l&&l.capability==='SUPPORTED'&&l.status!=='FAILED'),complete=status==='COMPLETE'&&requested.every(l=>l&&l.status==='COMPLETE');
 if(dimension==='requirement_implementation'){const m=code.result.metrics.find(m=>m.dimension==='work_item_implementation');available=available&&snapshotValid&&m.value!==null;complete=complete&&code.collection.status==='COMPLETE'&&m?.collection_status==='COMPLETE';}if(dimension==='executed_tests')available=available&&snapshotValid;
 const numerator=covered.filter(a=>has(byKind[population],a)).length,denominator=byKind[population].length,excluded_count=unique(diagnostics.filter(d=>rels.includes(d.relation)&&d.endpoint).map(d=>d.endpoint)).length,unknown_count=population==='REQUIREMENT'?requirements.filter(r=>['UNAVAILABLE','PARTIAL'].includes(r[field])).length:unique([...qualified.filter(r=>!r.qualified).map(r=>r.test),...conflictedTests]).filter(a=>has(byKind.TEST,a)).length;
 return{dimension,numerator,denominator,value:available&&denominator?numerator/denominator:null,status:!available||!denominator?'UNAVAILABLE':complete&&numerator===denominator?'VERIFIED':complete&&!numerator?'MISSING':'PARTIAL',unknown_count,excluded_count,reason:!denominator?'EMPTY_POPULATION':!available?'LOOKUP_UNAVAILABLE':!complete?'INCOMPLETE_EVIDENCE':null,collection_status:status,boundaries:[c.boundary,...bounds.map(b=>b.identifier)]};});
 const result={rule_version:'offline-evidence-1',snapshot_valid:snapshotValid,requirements,paths,runs:qualified,metrics,outcomes:Object.fromEntries(outcomes.map(o=>[o,qualified.filter(r=>r.qualified&&r.outcome===o).length])),gaps,diagnostics,dropped,associations,collection_status:status};for(const [k,v] of Object.entries(result))if(Array.isArray(v))result[k]=v.sort(compareCanonical);return result;
}
export function validateVerification(section,code,fail){
 if(!code||!publicTraceValues(section)||!exact(section,['schema_version','collection','result'])||section.schema_version!=='1.0')fail();const c=section.collection;
 if(!exact(c,collectionKeys)||!validSnapshot(c.snapshot)||!safeToken(c.boundary)||!traceTimestamp(c.collected_at)||!statuses.includes(c.status)||!exact(c.limits,['artifacts','associations','runs','paths']))fail();
 for(const [k,max] of [['artifacts',10000],['associations',40000],['runs',10000],['paths',10000]])if(!count(c.limits[k])||c.limits[k]<1||c.limits[k]>max)fail();
 for(const [k,max] of [['artifacts',10000],['associations',40000],['runs',10000],['lookups',40000]])if(!Array.isArray(c[k])||c[k].length>max||unique(c[k]).length!==c[k].length)fail();
 for(const a of c.artifacts)if(!validNew(a)||a.kind==='VERIFICATION')fail();
 for(const a of c.associations){if(!exact(a,['source','target','relation','origin','boundary'])||!validNew(a.source)||!(validNew(a.target)||validLegacy(a.target))||!Object.hasOwn(relations,a.relation)||!['DIRECT_PROVIDER_LINK','DIRECT_SOURCE_LINK'].includes(a.origin)||!safeToken(a.boundary))fail();const [source,target]=relations[a.relation];if(a.source.kind!==source||a.target.kind!==target)fail();if(kinds.includes(a.target.kind)&&(a.source.scope!==a.target.scope||a.source.instance!==a.target.instance))fail();if(a.relation==='REQUIREMENT_WORK_ITEM'&&a.source.scope!==a.target.scope)fail();}
 for(const r of c.runs)if(!exact(r,['reference','test','target','observed_at','outcome','boundary','group'])||!validNew(r.reference)||r.reference.kind!=='VERIFICATION'||!validNew(r.test)||r.test.kind!=='TEST'||r.reference.scope!==r.test.scope||r.reference.instance!==r.test.instance||!validSnapshot(r.target)||!traceTimestamp(r.observed_at)||!outcomes.includes(r.outcome)||!safeToken(r.boundary)||(r.group!==null&&!safeToken(r.group)))fail();
 for(const l of c.lookups){if(!exact(l,['endpoint','relation','population','direction','status','capability'])||!['OUTBOUND','INBOUND'].includes(l.direction)||!statuses.includes(l.status)||!caps.includes(l.capability))fail();if(l.population!==null){if(!['REQUIREMENT','TEST','ARCHITECTURE_DOCUMENT'].includes(l.population)||l.endpoint!==null||l.relation!==null||l.direction!=='OUTBOUND')fail();}else if(!validNew(l.endpoint)||!Object.hasOwn(relations,l.relation)||l.endpoint.kind!==relations[l.relation][l.direction==='OUTBOUND'?0:1])fail();}
 if(!exact(section.result,resultKeys))fail();const supplied=structuredClone(section.result);for(const [k,v] of Object.entries(supplied))if(Array.isArray(v))supplied[k]=v.sort(compareCanonical);if(!same(supplied,derivePortable(c,code)))fail();
}
export function portablePresentation(section,code){const c=section.collection,r=section.result;return{...r,schema_version:'v0.4-public-1',synthetic:false,warning:'PASS is a historical declared observation for that exact test version and target snapshot. It does not establish requirement correctness, sufficient coverage or acceptance readiness.',boundary:c.boundary,collected_at:c.collected_at,snapshot:c.snapshot,artifacts:c.artifacts,lookups:c.lookups,code_traceability:code};}

export function canonicalPortable(report){
 const normalize=v=>Array.isArray(v)?v.map(normalize):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,item])=>[k,['as_of','retrieved_at','merged_at','submitted_at','first_activity','last_activity','collected_at','observed_at','start','end'].includes(k)&&typeof item==='string'?canonicalTraceTime(item):normalize(item)])):v;
 const out=stable(normalize(report));
 if(out.verification_evidence){for(const k of ['artifacts','associations','runs','lookups'])out.verification_evidence.collection[k].sort(compareCanonical);for(const [k,v] of Object.entries(out.verification_evidence.result))if(Array.isArray(v))v.sort(compareCanonical);}
 return out;
}

export function boundedPortable(value,depth=0){
 if(depth>64)throw Error('Invalid portable report.');
 if(typeof value==='number'&&!Number.isFinite(value))throw Error('Invalid portable report.');
 if(typeof value==='string'){for(const c of value){const n=c.codePointAt(0);if(n>=0xd800&&n<=0xdfff)throw Error('Invalid portable report.');}}
 else if(Array.isArray(value)){for(const item of value)boundedPortable(item,depth+1);}
 else if(value&&typeof value==='object'){for(const [k,v] of Object.entries(value)){boundedPortable(k,depth+1);boundedPortable(v,depth+1);}}
}

export function absentCode(){return {"schema_version":"1.0","collection":{"status":"FAILED","component_strategy":{"name":"directory","configuration":"depth-2"},"boundaries":[],"work_items":[],"populations":{"pull_requests":[],"merged_pull_requests":[],"commits":[],"changed_paths":[]},"observed_links":[],"lookups":[],"diagnostics":[]},"result":{"derivation_version":"offline-1","summary":"UNAVAILABLE","direct_links":[],"derived_links":[],"paths":[],"gaps":[],"artifacts":[],"metrics":[{"dimension":"commit_intent","numerator":0,"denominator":0,"value":null,"status":"UNAVAILABLE","collection_status":"FAILED","boundaries":[],"sources":[],"unknown_count":0,"excluded_count":0,"reason":"EMPTY_POPULATION","component":null},{"dimension":"merged_pr_intent","numerator":0,"denominator":0,"value":null,"status":"UNAVAILABLE","collection_status":"FAILED","boundaries":[],"sources":[],"unknown_count":0,"excluded_count":0,"reason":"EMPTY_POPULATION","component":null},{"dimension":"work_item_implementation","numerator":0,"denominator":0,"value":null,"status":"UNAVAILABLE","collection_status":"FAILED","boundaries":[],"sources":[],"unknown_count":0,"excluded_count":0,"reason":"EMPTY_POPULATION","component":null}],"diagnostics":[]}};}
export function validatePublicEnvelope(r,fail){
 const allow=(v,name)=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!publicSchemas[name].includes(k)))fail();};
 const paths=v=>{if(typeof v==='string'&&(v.startsWith('/')||/(?:[A-Za-z]:[\\/]|\\\\)/.test(v)))fail();else if(Array.isArray(v))v.forEach(paths);else if(v&&typeof v==='object')for(const [k,item] of Object.entries(v)){paths(k);paths(item);}};
 if(!publicTraceValues(r))fail();paths(r);allow(r,'envelope');
 if(r.model!=='experimental-v0.1'||!Number.isSafeInteger(r.commit_count)||r.commit_count<0||!traceTimestamp(r.as_of))fail();
 for(const name of ['source','warning','review_evidence_error'])if(r[name]!==undefined&&typeof r[name]!=='string')fail();if(r.shallow!==undefined&&typeof r.shallow!=='boolean')fail();
 for(const name of ['configuration','filters','filter_evidence'])if(r[name]!==undefined)allow(r[name],name);
 const signals=['change_ownership','recency','change_frequency','code_area_breadth','unique_contribution','historical_persistence'];
 const signalKeys=v=>{if(!v||typeof v!=='object'||Object.keys(v).some(k=>!signals.includes(k)))fail();};
 if(r.configuration?.weights!==undefined)signalKeys(r.configuration.weights);
 if(r.configuration?.component_depth!==undefined&&(!Number.isSafeInteger(r.configuration.component_depth)||r.configuration.component_depth<1))fail();for(const n of [...Object.values(r.configuration?.weights??{}),...(r.configuration?.half_life_days===undefined?[]:[r.configuration.half_life_days])])if(typeof n!=='number'||!Number.isFinite(n)||n<0)fail();
 for(const k of ['exclude_bots','exclude_generated'])if(r.filters?.[k]!==undefined&&typeof r.filters[k]!=='boolean')fail();
 if(!Array.isArray(r.components))fail();
 for(const c of r.components){allow(c,'component');if(!Array.isArray(c.contributors))fail();for(const p of c.contributors){allow(p,'person');signalKeys(p.signals);if(p.file_activity!==undefined&&(!p.file_activity||typeof p.file_activity!=='object'||Array.isArray(p.file_activity)))fail();for(const [path,a] of Object.entries(p.file_activity??{})){allow(a,'activity');if(!path.trim()||['additions','deletions','unknown_line_changes'].some(k=>!count(a[k]))||!Array.isArray(a.commits)||a.commits.some(x=>typeof x!=='string'||!x.trim())||new Set(a.commits).size!==a.commits.length||!traceTimestamp(a.first_activity)||!traceTimestamp(a.last_activity))fail();}for(const k of ['additions','deletions','unknown_line_changes'])if(p[k]!==undefined&&!count(p[k]))fail();if(typeof p.contributor!=='string'||!p.contributor.trim()||!Number.isSafeInteger(p.commits)||p.commits<0||!Array.isArray(p.files)||p.files.some(f=>typeof f!=='string'||!f.trim()))fail();}}
 for(const c of r.components){const m=c.file_contributors??{};if(!m||typeof m!=='object'||Array.isArray(m)||Object.entries(m).some(([k,v])=>!k.trim()||!Array.isArray(v)||v.some(x=>typeof x!=='string'||!x.trim())||new Set(v).size!==v.length))fail();}
 if(r.filter_evidence&&['excluded_file_changes','input_file_changes'].some(k=>!Number.isSafeInteger(r.filter_evidence[k])||r.filter_evidence[k]<0))fail();
 if(r.review_evidence){const review=r.review_evidence;allow(review,'review');const c=review.provenance;allow(c,'collection');allow(c.provenance,'provenance');if(!Array.isArray(c.pull_requests)||!Array.isArray(review.components))fail();for(const pr of c.pull_requests){allow(pr,'pr');allow(pr.author,'identity');if(!Array.isArray(pr.reviews))fail();for(const e of pr.reviews){allow(e,'event');if(e.reviewer!==null)allow(e.reviewer,'identity');}}for(const row of review.components)allow(row,'review_component');}
}
