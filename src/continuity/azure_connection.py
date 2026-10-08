"""Local Azure CLI boundary; configuration and credentials remain private."""
from argparse import Namespace
from dataclasses import dataclass
from datetime import datetime
import getpass
from pathlib import Path
import sys
import tomllib
from typing import Any
import warnings

from continuity.analysis.traceability import derive
from continuity.domain.models import DirectoryComponents
from continuity.domain.reviews import CollectionStatus
from continuity.reporting.traceability import traceability_to_json
from continuity.traceability_providers.azure_devops import AzureDevOpsTraceabilityProvider
from continuity.traceability_providers.azure_profile import (
    AzureApiProfile, AzureDevOpsDeployment, AzureDevOpsProfile, AzureIdentityMap, AzureLimits,
)
from continuity.traceability_providers.azure_transport import AzureHttpTransport


@dataclass(frozen=True, repr=False)
class Connection:
    profile: AzureDevOpsProfile
    identities: AzureIdentityMap
    collected_at: datetime
    snapshot: str
    component_depth: int


def _table(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ValueError("invalid connection configuration")
    return value


def _text(table: dict[str, Any], key: str) -> str:
    value = table[key]
    if not isinstance(value, str) or not value:
        raise ValueError("invalid connection configuration")
    return value


def _aliases(value: Any) -> tuple[tuple[int, str], ...]:
    if not isinstance(value, dict) or len(value) > 100_000:
        raise ValueError("invalid connection configuration")
    result = []
    for key, alias in value.items():
        if not isinstance(key, str) or not key.isascii() or not key.isdecimal() or str(int(key)) != key or not isinstance(alias, str):
            raise ValueError("invalid connection configuration")
        result.append((int(key), alias))
    return tuple(sorted(result))


def load_connection(path: Path) -> Connection:
    with path.open('rb') as stream:
        contents = stream.read(1_048_577)
    if len(contents) > 1_048_576:
        raise ValueError("invalid connection configuration")
    raw = _table(tomllib.loads(contents.decode('utf-8')), {'connection', 'publication', 'identities'}, {'limits'})
    c = _table(raw['connection'], {'deployment', 'api_profile', 'base_url', 'collection', 'project', 'repository', 'revision'},
               {'api_version', 'include_changes', 'include_artifact_relations'})
    p = _table(raw['publication'], {'instance_alias', 'project_alias', 'repository_alias', 'snapshot', 'collected_at', 'component_depth'})
    i = _table(raw['identities'], {'fingerprint', 'work_items', 'pull_requests'})
    for key in ('include_changes', 'include_artifact_relations'):
        if key in c and type(c[key]) is not bool:
            raise ValueError("invalid connection configuration")
    if 'api_version' in c:
        _text(c, 'api_version')
    limits = _table(raw.get('limits', {}), set(), set(AzureLimits.__dataclass_fields__))
    profile = AzureDevOpsProfile(
        deployment=AzureDevOpsDeployment(_text(c, 'deployment')),
        api_profile=AzureApiProfile(_text(c, 'api_profile')),
        base_url=_text(c, 'base_url'), collection=_text(c, 'collection'),
        project=_text(c, 'project'), repository=_text(c, 'repository'), revision=_text(c, 'revision'),
        instance_alias=_text(p, 'instance_alias'), project_alias=_text(p, 'project_alias'),
        repository_alias=_text(p, 'repository_alias'), api_version=c.get('api_version'),
        include_changes=c.get('include_changes', True), include_artifact_relations=c.get('include_artifact_relations', True),
        limits=AzureLimits(**limits),
    )
    stamp = datetime.fromisoformat(_text(p, 'collected_at'))
    if stamp.utcoffset() is None:
        raise ValueError("invalid connection configuration")
    depth = p['component_depth']
    if type(depth) is not int or not 1 <= depth <= 32:
        raise ValueError("invalid connection configuration")
    identities = AzureIdentityMap(_text(i, 'fingerprint'), _aliases(i['work_items']), _aliases(i['pull_requests']))
    from continuity.traceability_providers.azure_profile import public_alias
    snapshot = _text(p, 'snapshot')
    public_alias(snapshot)
    return Connection(profile, identities, stamp, snapshot, depth)


def run(args: Namespace) -> int:
    try:
        if not args.approve_publication:
            raise ValueError()
        config = load_connection(args.config)
    except (ValueError, TypeError, OSError, OverflowError, RecursionError):
        print('continuity: invalid or unapproved Azure connection configuration', file=sys.stderr)
        return 2
    pat = None
    try:
        if not args.anonymous:
            if not sys.stdin.isatty():
                raise ValueError()
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                pat = getpass.getpass('Azure read-only PAT (hidden): ')
            if not pat:
                raise ValueError()
        transport = AzureHttpTransport(config.profile, pat)
    except (ValueError, EOFError, KeyboardInterrupt, getpass.GetPassWarning, OSError):
        print('continuity: Azure authentication input unavailable', file=sys.stderr)
        return 2
    finally:
        pat = None
    try:
        evidence = AzureDevOpsTraceabilityProvider(config.profile, config.identities, config.collected_at,
                                                  config.snapshot, transport).acquire()
        output = traceability_to_json(derive(evidence, DirectoryComponents(config.component_depth)))
        print(output)
        return {CollectionStatus.COMPLETE: 0, CollectionStatus.PARTIAL: 3, CollectionStatus.FAILED: 4}[evidence.status]
    except KeyboardInterrupt:
        print('continuity: Azure acquisition interrupted', file=sys.stderr)
        return 2
    except (ValueError, TypeError, OSError, OverflowError, RecursionError):
        print('continuity: Azure acquisition processing failed', file=sys.stderr)
        return 2
