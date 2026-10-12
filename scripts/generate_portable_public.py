"""Generate v4-only shared allowlists and Python Unicode folding for offline browser parity."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from continuity.reporting.portable_public import SCHEMAS

def generate():
    folds={chr(i):chr(i).casefold() for i in range(0x110000) if chr(i).casefold()!=chr(i)}
    return ('// Generated v4 public allowlists and complete Python Unicode casefold. Legacy rules unchanged.\n'
            +'export const publicSchemas='+json.dumps({k:sorted(v) for k,v in SCHEMAS.items()},separators=(',',':'))+';\n'
            +'const folds='+json.dumps(folds,ensure_ascii=True,separators=(',',':'))+';\n'
            +"export const casefold=value=>Array.from(value,c=>folds[c]??c).join('');\n")

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'ui/dist/portable-public.js'
    if sys.argv[1:]==['--check']:
        if not path.exists() or path.read_text()!=generate():raise SystemExit('portable public boundary is stale')
    elif not sys.argv[1:]:path.write_text(generate())
    else:raise SystemExit('usage: generate_portable_public.py [--check]')
    print('portable public boundary matches Python authority')
