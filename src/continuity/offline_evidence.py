"""Two explicit regular inputs; no acquisition, inference or credential handling."""
import argparse
from pathlib import Path
import stat
import os
import sys
import tempfile

from continuity.reporting.portable import MAX_BYTES, loads, manifest_from_json, manifest_from_toml, with_verification_evidence, report_to_json
from continuity.reporting.traceability import validate_report_envelope, traceability_from_dict


def read_input(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError('invalid offline input')
    with os.fdopen(descriptor, 'rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('invalid offline input')
    return data


def run(args: argparse.Namespace) -> int:
    try:
        report = validate_report_envelope(loads(read_input(args.report)))
        if report.get('report_version') != '3.0' or 'traceability_evidence' not in report:
            raise ValueError('invalid snapshot input')
        code = traceability_from_dict(report['traceability_evidence'])
        parser = manifest_from_json if args.manifest.suffix.lower() == '.json' else manifest_from_toml
        collection = parser(read_input(args.manifest), code)
        output = report_to_json(with_verification_evidence(report, collection))
    except OSError:
        print('continuity: offline evidence I/O failed', file=sys.stderr)
        return 3
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError):
        print('continuity: invalid or unapproved offline evidence inputs', file=sys.stderr)
        return 2
    try:
        if args.output is None:
            print(output)
        else:
            # Exclusive atomic publication: never truncate/overwrite an input or output.
            destination = args.output
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                                 prefix='.ecl-evidence-', delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(output + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(temporary, destination)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    except OSError:
        print('continuity: offline evidence I/O failed', file=sys.stderr)
        return 3
    return 0
