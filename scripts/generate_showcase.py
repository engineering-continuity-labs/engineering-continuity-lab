"""Project-owned SYNTHETIC Atlas Commerce; existing derivations, no hand-made aggregates."""
from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from continuity.analysis.service import analyze
from continuity.analysis.reviews import analyze_reviews
from continuity.analysis.verification import derive
from continuity.domain.models import Author,Change,Commit,History,DirectoryComponents
from continuity.domain.reviews import (ReviewIdentity,ReviewEvent,ReviewState,PullRequestEvidence,
                                       ReviewEvidenceCollection,ProviderProvenance)
from continuity.scoring.model import ScoringConfig
from continuity.reporting.traceability import with_traceability
from continuity.reporting.verification import to_dict
from continuity.traceability_providers.verification_synthetic import fixture,STAMP


def showcase():
    evidence=fixture()
    authors=[Author('author-alpha','author-alpha@example.test'),Author('author-beta','author-beta@example.test'),Author('author-gamma','author-gamma@example.test')]
    records=[('a',0,['src/payments/retry.py']),('b',1,['tests/payments/test_retry.py']),('c',1,['src/catalog/timeout.py']),('d',0,['src/payments/timeout.py']),('e',0,['src/payments/retry.py']),('f',2,['src/orders/create.py','tests/orders/test_create.py']),('1',1,['src/identity/session.py']),('2',0,['src/payments/retry.py']),('3',2,['src/catalog/timeout.py']),('4',0,['src/payments/retry.py'])]
    history=History(evidence.snapshot.revision,tuple(Commit(char*40,authors[who],STAMP-timedelta(days=len(records)-i),tuple(Change(path,10+i,2) for path in paths)) for i,(char,who,paths) in enumerate(records)))
    config=ScoringConfig();git=analyze(history,DirectoryComponents(2),config,STAMP)
    report={'model':'experimental-v0.1','warning':'SYNTHETIC Atlas Commerce; Git activity is historical evidence, not employee performance.',
            'configuration':{'component_depth':2,'weights':dict(config.weights),'half_life_days':config.half_life_days},
            'revision':git.revision,'as_of':git.as_of.isoformat(),'shallow':git.shallow,'commit_count':git.commit_count,
            'components':[asdict(c) for c in git.components]}
    alpha=ReviewIdentity('reviewer-alpha');beta=ReviewIdentity('reviewer-beta');gamma=ReviewIdentity('reviewer-gamma');bot=ReviewIdentity('review-bot',is_bot=True)
    owners=[ReviewIdentity(a.name) for a in authors]
    def event(identifier,state,reviewer,minute=0,order=None):
        return ReviewEvent(identifier,ReviewState(state),reviewer,STAMP+timedelta(minutes=minute),minute if order is None else order)
    def pr(identifier,owner,paths,events):
        return PullRequestEvidence(identifier,owners[owner],STAMP+timedelta(hours=1),tuple(paths),tuple(events))
    prs=(pr('51',0,['src/payments/retry.py','tests/payments/test_retry.py'],[event('51-a0','COMMENTED',alpha),event('51-a1','APPROVED',alpha,order=1),event('51-self','APPROVED',owners[0]),event('51-bot','APPROVED',bot)]),
         pr('52',1,['src/payments/timeout.py','src/catalog/timeout.py'],[event('52-beta','CHANGES_REQUESTED',beta),event('52-comment','COMMENTED',gamma)]),
         pr('53',2,['src/payments/retry.py','tests/payments/test_retry.py','src/catalog/timeout.py'],[event('53-alpha','APPROVED',alpha)]),
         pr('54',0,['src/payments/timeout.py'],[event('54-comment','COMMENTED',gamma)]),
         pr('55',2,['src/orders/create.py','tests/orders/test_create.py'],[event('55-beta','APPROVED',beta),event('55-gamma','APPROVED',gamma)]),
         pr('56',1,['src/identity/session.py'],[event('56-old','APPROVED',beta),event('56-new','COMMENTED',beta,1)]))
    reviews=ReviewEvidenceCollection(ProviderProvenance('synthetic','demo-system','atlas-commerce-review-v1',STAMP+timedelta(hours=2)),prs)
    report['review_evidence']=asdict(analyze_reviews(reviews,DirectoryComponents(2)))
    report=with_traceability(report,evidence.code)
    return {'name':'Atlas Commerce','report':report,'verification':to_dict(derive(evidence))}


def generate():
    return '// Generated SYNTHETIC Atlas Commerce. Run scripts/generate_showcase.py; no real test execution.\nexport default '+json.dumps(showcase(),sort_keys=True,ensure_ascii=True,separators=(',',':'),default=lambda value:value.isoformat() if hasattr(value,'isoformat') else value)+';\n'

if __name__=='__main__':
    output=Path(__file__).resolve().parents[1]/'ui/dist/showcase.js'
    if sys.argv[1:]==['--check']:
        if not output.exists() or output.read_text()!=generate():
            raise SystemExit('synthetic showcase is stale')
        print('synthetic showcase matches fresh derivation')
    elif sys.argv[1:]:
        raise SystemExit('usage: generate_showcase.py [--check]')
    else:
        output.write_text(generate())
