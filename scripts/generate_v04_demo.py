"""Generate only project-owned synthetic v0.4 scenarios from actual derivation."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from continuity.analysis.verification import derive
from continuity.reporting.verification import to_dict
from continuity.traceability_providers.verification_synthetic import fixture
import json


def generate() -> str:
    scenarios = {name:to_dict(derive(fixture(name))) for name in ('BASE','PARTIAL','STALE_TARGET','CONFLICTING_RUN','EMPTY','UNSUPPORTED','FAILED','LIMIT')}
    return '// Generated SYNTHETIC v0.4 evidence; not a Git report envelope or actual test execution.\nexport default '+json.dumps(scenarios,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+';\n'


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[1]/'ui/dist/verification-sample.js'
    if '--check' in sys.argv:
        if not output.exists() or output.read_text()!=generate():
            raise SystemExit('synthetic v0.4 demo is out of date')
        print('synthetic v0.4 demo matches fresh Python derivation')
    else:
        output.write_text(generate())
