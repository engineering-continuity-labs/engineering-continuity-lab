"""Generate the explicitly SYNTHETIC offline core package; no provider access."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from continuity.reporting.engineering_review import compose, import_package
from continuity.reporting.portable import canonical
from continuity.traceability_providers.engineering_synthetic import sources


def generate() -> str:
    windows, delivery, quality = sources()
    root = Path(__file__).resolve().parents[1]
    from continuity.reporting.portable import loads
    legacy = loads((root / 'examples/v0.4-traceability-v3.json').read_bytes())
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
    if sys.argv[1:]:
        if not target.exists() or target.read_text() != value:
            raise SystemExit('synthetic engineering review is stale')
    else:
        target.write_text(value)
    print('SYNTHETIC engineering review matches source events and recomputation')
