"""
Utility functions and helpers for the OpenRecover suite.

This module centralises small helper routines used across the
scanner, parser and recovery components. Keeping these helpers in one
place avoids circular imports and makes it easier to stub or mock
functionality in tests.
"""

from __future__ import annotations
import os
import hashlib
from typing import Optional

def is_ntfs(path: str) -> bool:
    try:
        if os.name == "nt":
            return bool(path) and len(path) >= 2 and path[1] == ":"
        else:
            return os.path.exists(path)
    except Exception:
        return False

def read_sector(fh, offset: int, size: int) -> bytes:
    import os as _os
    if hasattr(_os, 'pread') and isinstance(fh, int):
        try:
            return _os.pread(fh, size, offset)
        except Exception:
            pass
    if isinstance(fh, int):
        with _os.fdopen(_os.dup(fh), 'rb', closefd=True) as f:
            f.seek(offset)
            return f.read(size)
    else:
        cur = fh.tell()
        fh.seek(offset)
        data = fh.read(size)
        fh.seek(cur)
        return data

def sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def normalize_carve_data(sig, data: bytes) -> bytes:
    from .carver import FileCarver
    try:
        footer = getattr(sig, 'footer', None)
        if footer:
            idx = data.find(footer, len(sig.header))
            if idx >= 0:
                if getattr(sig, 'name', '') == 'png':
                    return data[:idx + len(footer) + 4]
                return data[:idx + len(footer)]
        size_from = getattr(sig, 'size_from_header_iso_bmff', None)
        if size_from:
            off, szlen = size_from
            if len(data) >= off + szlen:
                box_size = int.from_bytes(data[off:off+szlen], 'big', signed=False)
                if box_size > 0 and box_size <= len(data):
                    return data[:box_size]
    except Exception:
        pass
    return data
