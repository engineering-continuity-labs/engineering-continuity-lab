"""Project-owned v0.4 SYNTHETIC fixtures; not a test runner or live adapter."""
from dataclasses import replace
from datetime import datetime, timezone

from continuity.analysis.traceability import derive as code_derive
from continuity.analysis.verification import snapshot_for
from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import Direction as D, TraceabilityCapability as C
from continuity.domain.verification import (Association, Collection, Kind as K, Limits, Lookup,
                                           Outcome, Reference, Relation as R, Run, _LEGAL)
from continuity.traceability_providers.synthetic import base_fixture

STAMP = datetime(2026,1,1,tzinfo=timezone.utc)
BOUNDARY = 'synthetic-evidence-v04'


def fixture(variant: str = 'BASE') -> Collection:
    code = code_derive(base_fixture())
    snapshot = snapshot_for(code,'approved-code-baseline-v1')
    def ref(kind: K, name: str, document: str = '') -> Reference:
        return Reference(kind,'synthetic-v04','demo-project',name,'v1',document)
    requirements = tuple(ref(K.REQUIREMENT,f'Q{i}') for i in range(1,5))
    tests = tuple(ref(K.TEST,f'T{i}') for i in range(1,5))
    documents = (ref(K.ARCHITECTURE_DOCUMENT,'ADR1','ADR'),ref(K.ARCHITECTURE_DOCUMENT,'ICD1','ICD'))
    runs = tuple(Run(ref(K.VERIFICATION,f'V{i}'),tests[i-1],snapshot,STAMP,outcome,BOUNDARY) for i,outcome in enumerate(Outcome,1))
    wis = {w.reference.identifier:w.reference for w in code.evidence.work_items}
    links = [Association(q,wis[str(1000+i)],R.REQUIREMENT_WORK_ITEM,BOUNDARY) for i,q in enumerate(requirements[:3],1)]
    links += [Association(t,requirements[i],R.TEST_REQUIREMENT,BOUNDARY) for t,i in zip(tests[:3],(0,1,0))]
    links += [Association(doc,requirements[i],R.DOCUMENT_REQUIREMENT,BOUNDARY) for i,doc in enumerate(documents)]
    component = next(a.artifact for a in code.artifacts if a.artifact.kind.value=='COMPONENT')
    links += [Association(documents[0],component,R.DOCUMENT_COMPONENT,BOUNDARY)]
    links += [Association(run.reference,run.test,R.VERIFICATION_TEST,BOUNDARY) for run in runs]
    artifacts = (*requirements,*tests,*documents)
    lookups = [Lookup(population=kind) for kind in (K.REQUIREMENT,K.TEST,K.ARCHITECTURE_DOCUMENT)]
    for artifact in (*artifacts,*(run.reference for run in runs)):
        for relation,(source,target) in _LEGAL.items():
            if artifact.kind == source:
                lookups.append(Lookup(artifact,relation))
            elif artifact.kind == target:
                lookups.append(Lookup(artifact,relation,direction=D.INBOUND))
    result = Collection(artifacts,tuple(links),runs,tuple(lookups),snapshot,code,BOUNDARY,STAMP)
    if variant == 'BASE':
        return result
    if variant == 'PARTIAL':
        return replace(result,status=S.PARTIAL,lookups=tuple(replace(l,status=S.PARTIAL) if l.relation==R.TEST_REQUIREMENT else l for l in lookups))
    if variant == 'STALE_TARGET':
        return replace(result,runs=tuple(replace(r,target=replace(snapshot,revision='e'*40)) for r in runs))
    if variant == 'CONFLICTING_RUN':
        return replace(result,runs=(*runs,replace(runs[0],outcome=Outcome.FAIL)))
    if variant == 'EMPTY':
        return replace(result,artifacts=(),associations=(),runs=(),lookups=tuple(l for l in lookups if l.population))
    if variant == 'UNSUPPORTED':
        return replace(result,lookups=tuple(replace(l,capability=C.UNSUPPORTED) if l.relation==R.TEST_REQUIREMENT else l for l in lookups))
    if variant == 'FAILED':
        return replace(fixture('EMPTY'),status=S.FAILED,lookups=tuple(replace(l,status=S.FAILED,capability=C.UNKNOWN) for l in lookups if l.population))
    if variant == 'NO_LINKS':
        return replace(result,associations=())
    if variant == 'LIMIT':
        return replace(result,limits=Limits(artifacts=5,associations=5,runs=2,paths=2))
    raise ValueError('unknown synthetic evidence scenario')
