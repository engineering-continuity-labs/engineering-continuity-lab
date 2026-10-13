"""Bounded nonblocking regular-file reads at private CLI input boundaries."""
import os
from pathlib import Path
import stat


def read_private(path: Path, limit: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('invalid private input')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('invalid private input')
        return data
    finally:
        os.close(descriptor)
