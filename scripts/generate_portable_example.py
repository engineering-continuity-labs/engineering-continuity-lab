"""Project-owned synthetic offline manifest example; no source content or real execution."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from generate_showcase import showcase
from continuity.reporting.portable import collection_to_dict
from continuity.traceability_providers.verification_synthetic import fixture

def toml_value(value):
    if value is None:
        return '""'  # Optional fields only; explicitly absent, never inferred.
    if isinstance(value, dict):
        return '{ ' + ', '.join(f'{k} = {toml_value(v)}' for k,v in sorted(value.items())) + ' }'
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def generate():
    c = collection_to_dict(fixture())
    lines = ['# SYNTHETIC example. Replace all aliases/snapshot/lookups with approved project evidence.',
             '# Empty optional fields denote absence. Complete lookup declarations are source assertions.',
             'manifest_version = "1.0"', 'publication_approved = true', '', '[collection]']
    for key in ('snapshot','boundary','collected_at','status','limits'):
        lines.append(f'{key} = {toml_value(c[key])}')
    for name in ('artifacts','associations','runs','lookups'):
        for item in c[name]:
            lines.extend(['',f'[[collection.{name}]]'])
            lines.extend(f'{key} = {toml_value(value)}' for key,value in sorted(item.items()))
    root = Path(__file__).resolve().parents[1]
    return {root/'examples/v0.4-evidence.toml':'\n'.join(lines)+'\n',
            root/'examples/v0.4-traceability-v3.json':json.dumps(showcase()['report'],sort_keys=True,ensure_ascii=True,indent=2,default=lambda value:value.isoformat() if hasattr(value,'isoformat') else str(value))+'\n'}

if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--check']):
        raise SystemExit('usage: generate_portable_example.py [--check]')
    for path, value in generate().items():
        if sys.argv[1:]:
            if not path.exists() or path.read_text() != value:
                raise SystemExit('portable examples are stale')
        else:
            path.write_text(value)
    print('synthetic portable examples match fresh derivation')
