"""
NTFS volume and MFT scanner.

This module provides rudimentary functionality to locate and iterate
over Master File Table (MFT) records on NTFS volumes. The
implementation is deliberately simple and conservative: it searches
for the ASCII ``FILE`` signature within a binary stream and returns
the surrounding bytes as candidate MFT records.

For production use this scanner should be replaced with a proper
NTFS parser that locates the $MFT metadata file, interprets run
lists, and honours the $Bitmap. The current implementation is
intended to illustrate the architecture and support basic testing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .rawio import RawDevice, to_raw_if_drive
from .utils import is_ntfs

@dataclass
class MFTRecord:
    """A minimal representation of an MFT record.

    Attributes
    ----------
    offset: int
        Byte offset within the volume at which the record was found.
    raw: bytes
        Raw bytes of the record. NTFS records are typically 1024
        bytes long but may be other sizes on some volumes.
    """
    offset: int
    raw: bytes

class NTFSScanner:
    """Scan NTFS volumes for candidate MFT records.

    This class encapsulates enumeration and scanning of NTFS
    partitions. It does not perform full NTFS parsing; instead it
    searches for the literal string ``b'FILE'`` in the raw volume
    data and treats each occurrence as the start of an MFT record.
    """

    def __init__(self, record_size: int = 1024) -> None:
        """Create a scanner.

        Parameters
        ----------
        record_size: int, optional
            Assumed size in bytes of each MFT record. Standard NTFS
            volumes use 1024 bytes per record. If set to zero the
            scanner will not attempt to slice the record and will
            return all bytes following the signature.
        """
        self.record_size = record_size

    def list_ntfs_volumes(self) -> List[str]:
        """Return a list of possible NTFS volumes on the system.

        On Windows this enumerates drive letters ``C:`` through ``Z:``
        and retains those which pass a basic NTFS heuristic via
        :func:`openrecover.utils.is_ntfs`. On POSIX systems it lists
        block devices in ``/dev`` matching typical patterns (e.g.
        ``sd*`` and ``nvme*``). The returned list may include paths
        that are not actually NTFS; the caller should validate before
        scanning.
        """
        vols: List[str] = []
        if os.name == "nt":
            for letter in map(chr, range(ord('C'), ord('Z') + 1)):
                drive = f"{letter}:"
                if is_ntfs(drive):
                    vols.append(drive)
            return vols
        else:
            try:
                for dev in os.listdir('/dev'):
                    if dev.startswith(('sd', 'nvme', 'disk')):
                        path = os.path.join('/dev', dev)
                        vols.append(path)
            except Exception:
                # Fallback: return empty list if /dev is inaccessible
                pass
            return vols

    def scan_volume(self, source: str, max_records: int = 0) -> Iterable[MFTRecord]:
        """Yield candidate MFT records from a volume or image file.

        Parameters
        ----------
        source: str
            Path to a block device, drive letter or image file. If
            ``source`` looks like a drive letter on Windows it will be
            converted into a raw device path using
            :func:`openrecover.rawio.to_raw_if_drive`.
        max_records: int, optional
            Maximum number of records to yield. ``0`` means no limit.

        Yields
        ------
        MFTRecord
            Candidate record with offset and raw bytes.
        """
        path = to_raw_if_drive(source)
        rd = RawDevice(path)
        # Determine total size if available
        total = rd.length or 0
        # Read in chunks and scan for signature
        chunk_size = 16 * 1024 * 1024  # 16 MiB
        overlap = 512  # keep small overlap to catch boundary matches
        offset = 0
        produced = 0
        while total == 0 or offset < total:
            try:
                data = rd.read_at(offset, chunk_size)
            except Exception:
                # skip ahead on error
                offset += self.record_size if self.record_size else 4096
                continue
            if not data:
                break
            start = 0
            while True:
                idx = data.find(b'FILE', start)
                if idx < 0:
                    break
                record_offset = offset + idx
                if self.record_size:
                    rec_bytes = rd.read_at(record_offset, self.record_size)
                else:
                    # Without a fixed record size return all bytes until next signature or end of chunk
                    next_idx = data.find(b'FILE', idx + 4)
                    end = next_idx if next_idx >= 0 else len(data)
                    rec_bytes = data[idx:end]
                yield MFTRecord(offset=record_offset, raw=rec_bytes)
                produced += 1
                if max_records and produced >= max_records:
                    rd.close()
                    return
                start = idx + 4
            if len(data) < chunk_size:
                break
            offset += chunk_size - overlap
        rd.close()
