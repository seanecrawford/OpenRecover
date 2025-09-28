"""
NTFS volume and MFT scanner.

This module provides rudimentary functionality to locate and iterate
over Master File Table (MFT) records on NTFS volumes. The
implementation is deliberately simple and conservative: it searches
for the ASCII ``FILE`` signature within a binary stream and returns
the surrounding bytes as candidate MFT records.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Iterable, List
from .rawio import RawDevice, to_raw_if_drive
from .utils import is_ntfs

@dataclass
class MFTRecord:
    offset: int
    raw: bytes

class NTFSScanner:
    def __init__(self, record_size: int = 1024) -> None:
        self.record_size = record_size

    def list_ntfs_volumes(self) -> List[str]:
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
                        vols.append(os.path.join('/dev', dev))
            except Exception:
                pass
            return vols

    def scan_volume(self, source: str, max_records: int = 0) -> Iterable[MFTRecord]:
        path = to_raw_if_drive(source)
        rd = RawDevice(path)
        total = rd.length or 0
        chunk_size = 16 * 1024 * 1024
        overlap = 512
        offset = 0
        produced = 0
        while total == 0 or offset < total:
            try:
                data = rd.read_at(offset, chunk_size)
            except Exception:
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
