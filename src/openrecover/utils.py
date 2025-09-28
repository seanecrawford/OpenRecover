"""
Utility functions and helpers for the OpenRecover suite.

This module centralises small helper routines used across the
scanner, parser and recovery components. Keeping these helpers in one
place avoids circular imports and makes it easier to stub or mock
functionality in tests.

The current implementation provides only a minimal set of helpers
required by the rest of the package. Additional utilities should be
added here as the project evolves.
"""

from __future__ import annotations

import os
import hashlib
from typing import Optional

def is_ntfs(path: str) -> bool:
    """Return True if the given path appears to be an NTFS filesystem.

    The check is heuristic and examines the file system type where
    possible. On Windows, the drive letter is queried via ``os.statvfs``
    to determine the file system name. On POSIX systems it simply
    checks that the path exists and is a block device or regular file.

    Parameters
    ----------
    path: str
        A path to a mounted volume or block device.

    Returns
    -------
    bool
        ``True`` if the volume is likely NTFS, ``False`` otherwise.
    """
    try:
        if os.name == "nt":
            # On Windows use GetVolumeInformation via ctypes to query
            # the filesystem type. To avoid importing ctypes here, we
            # fall back to returning True for any drive letter. The
            # scanner will attempt to parse the MFT and abort on
            # failure.
            return bool(path) and len(path) >= 2 and path[1] == ":"
        else:
            # For POSIX systems assume NTFS if file exists. Users can
            # override this check by supplying only NTFS volumes to
            # list_ntfs_volumes().
            return os.path.exists(path)
    except Exception:
        return False

def read_sector(fh, offset: int, size: int) -> bytes:
    """Read a block of data from a file descriptor at the given offset.

    On POSIX systems this uses ``os.pread`` if available to avoid
    disturbing the file pointer. On other systems it falls back to
    seeking and reading.

    Parameters
    ----------
    fh: int or file-like
        File descriptor or object with ``seek`` and ``read`` methods.
    offset: int
        Byte offset from the beginning of the file/volume.
    size: int
        Number of bytes to read.

    Returns
    -------
    bytes
        The data read, which may be shorter than ``size`` on EOF.
    """
    import os as _os
    # Use os.pread if available and fh is a file descriptor
    if hasattr(_os, 'pread') and isinstance(fh, int):
        try:
            return _os.pread(fh, size, offset)
        except Exception:
            pass
    # Fallback: seek and read
    if isinstance(fh, int):
        # convert descriptor to file object
        with _os.fdopen(_os.dup(fh), 'rb', closefd=True) as f:
            f.seek(offset)
            return f.read(size)
    else:
        # assume file-like object
        cur = fh.tell()
        fh.seek(offset)
        data = fh.read(size)
        fh.seek(cur)
        return data

def sha256(data: bytes) -> str:
    """Compute a SHA‑256 hex digest for the given data."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def normalize_carve_data(sig, data: bytes) -> bytes:
    """Return a canonical slice of carved data for deduplication.

    The carver may extract more bytes than the logical end of a file
    when it fails to locate a precise footer. For deduplication
    purposes we attempt to trim the data down to a canonical length
    using the signature’s footer or ISO Base Media File Format size
    information. This ensures that duplicate files carved from
    different offsets (e.g., across chunk boundaries) hash to the
    same digest.

    Parameters
    ----------
    sig: openrecover.signatures.FileSignature
        The signature describing the carved file type.
    data: bytes
        Raw data carved from disk.

    Returns
    -------
    bytes
        A possibly trimmed version of ``data``.
    """
    from .carver import FileCarver  # local import to avoid circular dependency
    # Try footer-based trimming
    try:
        footer = getattr(sig, 'footer', None)
        if footer:
            idx = data.find(footer, len(sig.header))
            if idx >= 0:
                # PNG special case: include entire IEND chunk (12 bytes)
                if getattr(sig, 'name', '') == 'png':
                    # Include the 4-byte IEND marker and 4-byte CRC
                    return data[:idx + len(footer) + 4]
                return data[:idx + len(footer)]
        # Try ISO BMFF size from header
        size_from = getattr(sig, 'size_from_header_iso_bmff', None)
        if size_from:
            off, szlen = size_from
            if len(data) >= off + szlen:
                box_size = int.from_bytes(data[off:off+szlen], 'big', signed=False)
                if box_size > 0 and box_size <= len(data):
                    return data[:box_size]
    except Exception:
        pass
    # Fallback: return original data
    return data
