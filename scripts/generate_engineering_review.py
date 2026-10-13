"""Generate the explicitly SYNTHETIC offline core package; no provider access."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from continuity.reporting.engineering_review import compose, import_package
from continuity.reporting.portable import canonical
from continuity.reporting.engineering_html import render
from continuity.traceability_providers.engineering_synthetic import sources


def generate() -> str:
    windows, delivery, quality = sources()
    root = Path(__file__).resolve().parents[1]
    from continuity.reporting.portable import loads
    legacy = loads((root / 'examples/v0.4-traceability-v3.json').read_bytes())
    from continuity.reporting.portable import with_verification_evidence
    from continuity.traceability_providers.verification_synthetic import fixture
    legacy = with_verification_evidence(legacy, fixture())
    # Explicit source-owner declarations for this fictional manager example.
    # These assertions do not infer membership from titles or names.
    components = {v['artifact']['identifier']: v['artifact'] for v in legacy['traceability_evidence']['result']['artifacts']
                  if v['artifact']['kind'] == 'COMPONENT'}
    assignments = {'current-0': 'src/payments', 'current-1': 'src/payments', 'current-2': 'src/catalog', 'current-3': 'src/catalog',
                   'previous-0': 'src/payments', 'previous-1': 'src/payments', 'previous-2': 'src/catalog', 'previous-3': 'src/catalog',
                   'open': 'src/payments', 'B1': 'src/catalog', 'B2': 'src/payments', 'B3': 'src/catalog', 'B4': 'src/payments',
                   '0': 'src/payments', '1': 'src/catalog', '2': 'src/payments', '3': 'src/catalog'}
    for source in (delivery, quality):
        source.update(mapping_revision=legacy['revision'], mapping_complete=True)
        for population in ('work_items', 'pull_requests', 'builds'):
            for record in source[population]:
                identifier = record['reference'][-1]
                if identifier in assignments:
                    source['mappings'].append({'record_ref': record['reference'], 'component_ref': components[assignments[identifier]],
                                               'mapping_id': population + '-' + identifier, 'origin': 'DECLARED_MAPPING',
                                               'boundary': 'synthetic-base', 'completeness': 'COMPLETE'})
    package = compose(assessment_id='synthetic-atlas-review', system='atlas', windows=windows,
                      delivery=delivery, quality=quality, ecl_report=legacy)
    output = canonical(package)
    import_package(output)
    return output + '\n'


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--check']):
        raise SystemExit('usage: generate_engineering_review.py [--check]')
    target = Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json'
    value = generate()
    html_target = Path(__file__).resolve().parents[1] / 'ui/dist/engineering-review.html'
    html_value = render(import_package(value), synthetic=True) + '\n'
    if sys.argv[1:]:
        if not target.exists() or target.read_text() != value:
            raise SystemExit('synthetic engineering review is stale')
        if not html_target.exists() or html_target.read_text() != html_value:
            raise SystemExit('synthetic engineering HTML is stale')
    else:
        target.write_text(value)
        html_target.write_text(html_value)
    print('SYNTHETIC engineering review matches source events and recomputation')
